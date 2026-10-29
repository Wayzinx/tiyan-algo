"""全栈工程师 SQL 专项题库。"""


def _shop_seed():
    users = []
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都"]
    channels = ["自然搜索", "广告投放", "老客推荐", "直播间"]
    for user_id in range(1, 31):
        users.append((
            user_id,
            "用户%02d" % user_id,
            cities[user_id % len(cities)] if user_id not in (7, 19) else None,
            "2026-%02d-%02d %02d:00:00" % (((user_id - 1) % 6) + 1, ((user_id * 3) % 26) + 1, 8 + user_id % 10),
            channels[user_id % len(channels)],
            user_id - 1 if user_id in (6, 12, 18, 24, 30) else None,
        ))
    merchants = [
        (1, "山海百货", "综合百货", "上海", "2025-11-01 10:00:00"),
        (2, "晨光数码", "数码家电", "深圳", "2025-12-10 09:30:00"),
        (3, "四季生鲜", "食品生鲜", "杭州", "2026-01-05 11:20:00"),
        (4, "远行户外", "运动户外", "成都", "2026-02-14 15:45:00"),
    ]
    products = [
        (1, 1, "SKU-A001", "保温杯", "家居", 59.00, 1),
        (2, 1, "SKU-A002", "收纳箱", "家居", 89.00, 1),
        (3, 1, "SKU-A003", "雨伞", "出行", 39.00, 1),
        (4, 2, "SKU-B001", "蓝牙耳机", "数码", 199.00, 1),
        (5, 2, "SKU-B002", "充电宝", "数码", 129.00, 1),
        (6, 2, "SKU-B003", "键盘", "数码", 299.00, 1),
        (7, 3, "SKU-C001", "坚果礼盒", "食品", 168.00, 1),
        (8, 3, "SKU-C002", "冷萃咖啡", "食品", 79.00, 1),
        (9, 3, "SKU-C003", "有机大米", "食品", 119.00, 1),
        (10, 4, "SKU-D001", "登山包", "户外", 259.00, 1),
        (11, 4, "SKU-D002", "速干衣", "户外", 139.00, 1),
        (12, 4, "SKU-D003", "露营灯", "户外", 99.00, 0),
    ]
    orders, items, payments = [], [], []
    item_id = 1
    payment_id = 1
    statuses = ["COMPLETED", "PAID", "SHIPPED", "CANCELED", "REFUNDED"]
    pay_methods = ["BALANCE", "CARD", "WALLET", "BANK"]
    product_map = {p[0]: p for p in products}
    for order_id in range(1, 121):
        month = ((order_id - 1) % 6) + 1
        day = ((order_id * 7) % 27) + 1
        hour = 9 + order_id % 12
        user_id = ((order_id * 7) % 27) + 1
        if order_id in (118, 119):
            month = 6
            day = 10 + (order_id - 118)
            user_id = 5
        if order_id in (8, 16, 24, 32, 40, 48):
            user_id = 3
        merchant_id = ((order_id - 1) % 4) + 1
        status = statuses[order_id % len(statuses)]
        if order_id % 17 == 0:
            status = "CANCELED"
        if order_id % 23 == 0:
            status = "REFUNDED"
        order_time = "2026-%02d-%02d %02d:%02d:00" % (month, day, hour, (order_id * 5) % 60)
        paid_at = None if status == "CANCELED" and order_id % 2 == 0 else "2026-%02d-%02d %02d:%02d:00" % (month, day, min(hour + 1, 23), (order_id * 5 + 3) % 60)
        canceled_at = "2026-%02d-%02d %02d:%02d:00" % (month, day, min(hour + 2, 23), (order_id * 5 + 9) % 60) if status == "CANCELED" else None
        shipping_fee = 0.0 if order_id % 4 == 0 else 6.0
        coupon_amount = [0.0, 5.0, 10.0, 20.0][order_id % 4]
        item_count = 3 if order_id % 4 in (0, 1) else 2
        product_ids = [((merchant_id - 1) * 3 + ((order_id + j) % 3) + 1) for j in range(item_count)]
        order_total = shipping_fee - coupon_amount
        for product_id in product_ids:
            product = product_map[product_id]
            quantity = 1 + ((order_id + product_id) % 3 == 0)
            refund_quantity = 1 if status == "REFUNDED" and product_id == product_ids[0] else 0
            item_amount = round(quantity * product[5], 2)
            order_total += item_amount
            items.append((item_id, order_id, product_id, quantity, product[5], refund_quantity, item_amount))
            item_id += 1
        order_total = round(max(order_total, 0), 2)
        if order_id in (12, 36, 72):
            order_total = 299.00
        address_city = cities[(user_id + merchant_id) % len(cities)] if order_id not in (15, 55, 95) else None
        remark = None if order_id % 9 else "需要延迟配送"
        orders.append((order_id, user_id, merchant_id, "SO2026%04d" % order_id, status, order_time, paid_at, canceled_at, order_total, shipping_fee, coupon_amount, address_city, remark))
        if paid_at:
            paid_amount = 0.0 if status == "CANCELED" else order_total
            pay_status = "REFUNDED" if status == "REFUNDED" else "SUCCESS"
            refunded_at = "2026-%02d-%02d %02d:%02d:00" % (month, min(day + 2, 28), 10, order_id % 60) if status == "REFUNDED" else None
            payments.append((payment_id, order_id, pay_methods[order_id % len(pay_methods)], paid_amount, pay_status, paid_at, refunded_at))
            payment_id += 1
    def values(rows):
        out = []
        for row in rows:
            vals = []
            for value in row:
                if value is None:
                    vals.append("NULL")
                elif isinstance(value, str):
                    vals.append("'" + value.replace("'", "''") + "'")
                else:
                    vals.append(str(value))
            out.append("(" + ", ".join(vals) + ")")
        return ",\n".join(out)
    return """
INSERT INTO users (user_id, user_name, city, register_time, channel, referrer_user_id) VALUES
%s;
INSERT INTO merchants (merchant_id, merchant_name, category, city, joined_at) VALUES
%s;
INSERT INTO products (product_id, merchant_id, sku, product_name, category, price, is_active) VALUES
%s;
INSERT INTO orders (order_id, user_id, merchant_id, order_no, status, order_time, paid_at, canceled_at, total_amount, shipping_fee, coupon_amount, address_city, remark) VALUES
%s;
INSERT INTO order_items (item_id, order_id, product_id, quantity, unit_price, refund_quantity, item_amount) VALUES
%s;
INSERT INTO payments (payment_id, order_id, pay_method, amount, status, paid_at, refunded_at) VALUES
%s;
""" % (values(users), values(merchants), values(products), values(orders), values(items), values(payments))


def _logistics_seed():
    warehouses = [
        (1, "华东一仓", "上海", "华东"),
        (2, "华南一仓", "广州", "华南"),
        (3, "华北一仓", "北京", "华北"),
        (4, "西南一仓", "成都", "西南"),
    ]
    couriers = [
        (1, "骑手01", "13000000001", 4.8),
        (2, "骑手02", "13000000002", 4.6),
        (3, "骑手03", "13000000003", 4.9),
        (4, "骑手04", "13000000004", 4.4),
        (5, "骑手05", "13000000005", 4.7),
        (6, "骑手06", "13000000006", 4.5),
    ]
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京"]
    statuses = ["CREATED", "PICKED", "IN_TRANSIT", "DELIVERED", "EXCEPTION"]
    shipments, events = [], []
    event_id = 1
    event_types = ["CREATED", "PICKED", "DEPARTED", "ARRIVED", "OUT_FOR_DELIVERY", "DELIVERED"]
    for shipment_id in range(1, 111):
        month = ((shipment_id - 1) % 6) + 1
        day = ((shipment_id * 5) % 27) + 1
        hour = 6 + shipment_id % 14
        warehouse_id = ((shipment_id - 1) % 4) + 1
        courier_id = ((shipment_id * 2) % 6) + 1
        status = statuses[shipment_id % len(statuses)]
        if shipment_id % 9 == 0:
            status = "DELIVERED"
        if shipment_id % 16 == 0:
            status = "EXCEPTION"
        created_at = "2026-%02d-%02d %02d:00:00" % (month, day, hour)
        shipped_at = "2026-%02d-%02d %02d:30:00" % (month, day, min(hour + 2, 23)) if status != "CREATED" else None
        delivered_at = None
        if status == "DELIVERED":
            delivered_day = min(day + (shipment_id % 4) + 1, 28)
            delivered_at = "2026-%02d-%02d %02d:20:00" % (month, delivered_day, min(hour + 6, 23))
        promised_hours = [24, 48, 72][shipment_id % 3]
        destination_city = cities[(shipment_id + warehouse_id) % len(cities)]
        package_weight = round(0.5 + (shipment_id % 8) * 0.7, 2)
        last_event_time = delivered_at or shipped_at or created_at
        shipments.append((shipment_id, 10000 + shipment_id, warehouse_id, courier_id, status, created_at, shipped_at, delivered_at, promised_hours, destination_city, package_weight, last_event_time))
        base_events = ["CREATED"] if status == "CREATED" else event_types[:(6 if status == "DELIVERED" else 4)]
        if status == "EXCEPTION":
            base_events = ["CREATED", "PICKED", "DEPARTED", "EXCEPTION"]
        if shipment_id in (9, 45) and status == "DELIVERED":
            base_events = ["CREATED", "PICKED", "DEPARTED", "EXCEPTION", "OUT_FOR_DELIVERY", "DELIVERED"]
        for pos, event_type in enumerate(base_events):
            ev_day = min(day + pos // 3, 28)
            ev_hour = min(hour + pos * 2, 23)
            event_time = "2026-%02d-%02d %02d:%02d:00" % (month, ev_day, ev_hour, (shipment_id + pos * 7) % 60)
            events.append((event_id, shipment_id, event_time, event_type, cities[(shipment_id + pos) % len(cities)], "系统" if pos == 0 else "分拣员", None if event_type != "EXCEPTION" else "地址信息待确认"))
            event_id += 1
        if shipment_id % 10 == 0:
            events.append((event_id, shipment_id, "2026-%02d-%02d %02d:%02d:00" % (month, day, hour, shipment_id % 60), "CREATED", cities[shipment_id % len(cities)], "系统", "重复上报"))
            event_id += 1
        if shipment_id % 13 == 0:
            events.append((event_id, shipment_id, "2026-%02d-%02d %02d:%02d:00" % (month, day, max(hour - 1, 0), shipment_id % 60), "CREATED", cities[(shipment_id + 1) % len(cities)], "补偿任务", "乱序补写"))
            event_id += 1
    inventory, checks = [], []
    skus = ["SKU-A001", "SKU-A002", "SKU-A003", "SKU-B001", "SKU-B002", "SKU-B003", "SKU-C001", "SKU-C002", "SKU-C003", "SKU-D001", "SKU-D002", "SKU-D003"]
    inventory_id = 1
    check_id = 1
    for warehouse_id in range(1, 5):
        for idx, sku in enumerate(skus, start=1):
            available = 40 + warehouse_id * 8 + (idx * 7) % 55
            locked = (idx * warehouse_id) % 13
            damaged = idx % 4
            inventory.append((inventory_id, warehouse_id, sku, "B2026%02d%02d" % (warehouse_id, idx), available, locked, damaged, "2026-06-%02d 18:00:00" % (((idx + warehouse_id) % 27) + 1)))
            checked = available + locked - damaged + (3 if idx % 5 == 0 else (-2 if idx % 7 == 0 else 0))
            checks.append((check_id, warehouse_id, sku, checked, "2026-06-%02d 21:00:00" % (((idx + warehouse_id + 3) % 27) + 1)))
            inventory_id += 1
            check_id += 1
    def values(rows):
        out = []
        for row in rows:
            vals = []
            for value in row:
                if value is None:
                    vals.append("NULL")
                elif isinstance(value, str):
                    vals.append("'" + value.replace("'", "''") + "'")
                else:
                    vals.append(str(value))
            out.append("(" + ", ".join(vals) + ")")
        return ",\n".join(out)
    return """
INSERT INTO warehouses (warehouse_id, warehouse_name, city, region) VALUES
%s;
INSERT INTO couriers (courier_id, courier_name, phone, rating) VALUES
%s;
INSERT INTO shipments (shipment_id, order_id, warehouse_id, courier_id, status, created_at, shipped_at, delivered_at, promised_hours, destination_city, package_weight, last_event_time) VALUES
%s;
INSERT INTO tracking_events (event_id, shipment_id, event_time, event_type, event_city, operator, note) VALUES
%s;
INSERT INTO inventory (inventory_id, warehouse_id, product_sku, batch_no, available_qty, locked_qty, damaged_qty, updated_at) VALUES
%s;
INSERT INTO inventory_checks (check_id, warehouse_id, product_sku, checked_qty, checked_at) VALUES
%s;
""" % (values(warehouses), values(couriers), values(shipments), values(events), values(inventory), values(checks))


SQL_DATASETS = dict(
    shop=dict(
        title="电商交易分析数据集",
        desc="今天是 2026-06-30。数据集包含 users 用户、merchants 商家、products 商品、orders 订单、order_items 订单明细、payments 支付流水。users 与 orders 是一对多，merchants 与 products、orders 是一对多，orders 与 order_items、payments 是一对多。数据覆盖 2026-01 到 2026-06，包含取消、退款、未下单用户、同一天多单、相同金额并列、NULL 城市和备注、跨月订单，适合练习电商运营和履约前的查询分析。",
        ddl="""
CREATE TABLE users (
  user_id INTEGER PRIMARY KEY,
  user_name TEXT NOT NULL,
  city TEXT,
  register_time TEXT NOT NULL,
  channel TEXT NOT NULL,
  referrer_user_id INTEGER
);
CREATE TABLE merchants (
  merchant_id INTEGER PRIMARY KEY,
  merchant_name TEXT NOT NULL,
  category TEXT NOT NULL,
  city TEXT NOT NULL,
  joined_at TEXT NOT NULL
);
CREATE TABLE products (
  product_id INTEGER PRIMARY KEY,
  merchant_id INTEGER NOT NULL,
  sku TEXT NOT NULL,
  product_name TEXT NOT NULL,
  category TEXT NOT NULL,
  price REAL NOT NULL,
  is_active INTEGER NOT NULL
);
CREATE TABLE orders (
  order_id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  merchant_id INTEGER NOT NULL,
  order_no TEXT NOT NULL,
  status TEXT NOT NULL,
  order_time TEXT NOT NULL,
  paid_at TEXT,
  canceled_at TEXT,
  total_amount REAL NOT NULL,
  shipping_fee REAL NOT NULL,
  coupon_amount REAL NOT NULL,
  address_city TEXT,
  remark TEXT
);
CREATE TABLE order_items (
  item_id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL,
  unit_price REAL NOT NULL,
  refund_quantity INTEGER NOT NULL,
  item_amount REAL NOT NULL
);
CREATE TABLE payments (
  payment_id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL,
  pay_method TEXT NOT NULL,
  amount REAL NOT NULL,
  status TEXT NOT NULL,
  paid_at TEXT NOT NULL,
  refunded_at TEXT
);
""",
        seed=_shop_seed(),
    ),
    logistics=dict(
        title="履约物流分析数据集",
        desc="今天是 2026-06-30。数据集包含 warehouses 仓库、shipments 运单、tracking_events 轨迹事件、couriers 配送员、inventory 库存、inventory_checks 盘点结果。shipments 关联仓库和配送员，tracking_events 按运单多次写入且刻意包含乱序补写和重复事件，inventory 与盘点表按仓库和 SKU 对账。数据覆盖 2026-01 到 2026-06，适合练习最新状态、签收时效、异常运单、库存差异和高写入轨迹查询。",
        ddl="""
CREATE TABLE warehouses (
  warehouse_id INTEGER PRIMARY KEY,
  warehouse_name TEXT NOT NULL,
  city TEXT NOT NULL,
  region TEXT NOT NULL
);
CREATE TABLE couriers (
  courier_id INTEGER PRIMARY KEY,
  courier_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  rating REAL NOT NULL
);
CREATE TABLE shipments (
  shipment_id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL,
  warehouse_id INTEGER NOT NULL,
  courier_id INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  shipped_at TEXT,
  delivered_at TEXT,
  promised_hours INTEGER NOT NULL,
  destination_city TEXT NOT NULL,
  package_weight REAL NOT NULL,
  last_event_time TEXT
);
CREATE TABLE tracking_events (
  event_id INTEGER PRIMARY KEY,
  shipment_id INTEGER NOT NULL,
  event_time TEXT NOT NULL,
  event_type TEXT NOT NULL,
  event_city TEXT NOT NULL,
  operator TEXT NOT NULL,
  note TEXT
);
CREATE TABLE inventory (
  inventory_id INTEGER PRIMARY KEY,
  warehouse_id INTEGER NOT NULL,
  product_sku TEXT NOT NULL,
  batch_no TEXT NOT NULL,
  available_qty INTEGER NOT NULL,
  locked_qty INTEGER NOT NULL,
  damaged_qty INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE inventory_checks (
  check_id INTEGER PRIMARY KEY,
  warehouse_id INTEGER NOT NULL,
  product_sku TEXT NOT NULL,
  checked_qty INTEGER NOT NULL,
  checked_at TEXT NOT NULL
);
""",
        seed=_logistics_seed(),
    ),
)


SQL_QUERIES = [
    dict(
        id="q1",
        order=1,
        dataset="shop",
        level="入门",
        topic="基础过滤排序分页",
        title="最近成功支付订单分页",
        question="运营要抽查 2026 年 6 月已经成功支付且未取消的订单，请输出 order_id、user_id、total_amount、paid_at，按 paid_at 倒序、order_id 倒序取前 10 条。",
        hint="先筛 paid_at 不为空，再排除取消状态，并把排序键补到唯一。",
        answer="""
SELECT order_id, user_id, total_amount, paid_at
FROM orders
WHERE paid_at IS NOT NULL
  AND status <> 'CANCELED'
  AND paid_at >= '2026-06-01 00:00:00'
  AND paid_at < '2026-07-01 00:00:00'
ORDER BY paid_at DESC, order_id DESC
LIMIT 10;
""",
        ordered=True,
        explain="这题的约束是只看已经支付且没有取消的订单，所以用 paid_at IS NOT NULL 和 status 过滤。时间范围用半开区间可以命中普通时间索引，避免对字段做函数。ORDER BY 增加 order_id 作为唯一兜底，分页结果才稳定。MySQL 8 写法基本相同，也推荐半开区间而不是 DATE(paid_at)='2026-06-xx'。",
        pitfalls=["只按月份函数过滤会让时间列索引失效", "只 ORDER BY paid_at，时间相同的行分页可能抖动", "忘记排除 CANCELED 会把未履约订单算进抽查池"],
    ),
    dict(
        id="q2",
        order=2,
        dataset="shop",
        level="入门",
        topic="基础聚合",
        title="各订单状态数量",
        question="客服主管想看 2026-01 到 2026-06 各订单状态的数量，请输出 status、order_count，按 order_count 从高到低、status 从小到大排序。",
        hint="GROUP BY 状态即可，排序要补 status 保证唯一顺序。",
        answer="""
SELECT status, COUNT(*) AS order_count
FROM orders
WHERE order_time >= '2026-01-01 00:00:00'
  AND order_time < '2026-07-01 00:00:00'
GROUP BY status
ORDER BY order_count DESC, status ASC;
""",
        ordered=True,
        explain="状态看板的失败模式是把不同月份或测试数据混在一起，因此先限定 2026 上半年。COUNT(*) 统计订单行，不受 NULL 字段影响。排序补 status 可以让数量并列时结果稳定。MySQL 8 与 SQLite 写法一致。",
        pitfalls=["COUNT(paid_at) 会漏掉未支付取消单", "不限定时间会把历史口径混进来", "并列时不补排序键会导致校验顺序不稳定"],
    ),
    dict(
        id="q3",
        order=3,
        dataset="shop",
        level="入门",
        topic="内连接",
        title="商品销量排行",
        question="类目运营要看已产生订单明细的商品销量，请输出 product_id、product_name、sold_qty、sales_amount，按 sold_qty 倒序、sales_amount 倒序、product_id 升序取前 10。",
        hint="订单明细 JOIN 商品表，销量用 quantity 求和。",
        answer="""
SELECT p.product_id, p.product_name,
       SUM(oi.quantity) AS sold_qty,
       ROUND(SUM(oi.item_amount), 2) AS sales_amount
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_name
ORDER BY sold_qty DESC, sales_amount DESC, p.product_id ASC
LIMIT 10;
""",
        ordered=True,
        explain="商品销量来自明细层而不是订单层，因为一个订单可包含多个商品。JOIN 后按商品聚合，金额用明细金额求和，避免订单总额被一个订单内多商品重复分摊。MySQL 8 在 ONLY_FULL_GROUP_BY 下也需要把非聚合列放入 GROUP BY。",
        pitfalls=["用订单总额按商品汇总会重复计算", "只按商品名分组可能把同名不同 SKU 合并", "退款数量如果题目没有要求净销量，不应自行扣减"],
    ),
    dict(
        id="q4",
        order=4,
        dataset="shop",
        level="入门",
        topic="LEFT JOIN",
        title="未下单用户",
        question="增长同学想找注册后从未下单的用户做召回，请输出 user_id、user_name、register_time，按 register_time 升序、user_id 升序排序。",
        hint="用户表 LEFT JOIN 订单表，然后找右表主键为 NULL 的行。",
        answer="""
SELECT u.user_id, u.user_name, u.register_time
FROM users u
LEFT JOIN orders o ON o.user_id = u.user_id
WHERE o.order_id IS NULL
ORDER BY u.register_time ASC, u.user_id ASC;
""",
        ordered=True,
        explain="需求的主体是全量用户，失败模式是内连接会直接丢掉没有订单的用户。LEFT JOIN 后用 o.order_id IS NULL 找无匹配记录，排序使用注册时间加 user_id 稳定输出。MySQL 8 写法一致，也可用 NOT EXISTS。",
        pitfalls=["使用 INNER JOIN 会完全看不到未下单用户", "在 WHERE 里写订单状态条件会把 LEFT JOIN 变成事实内连接", "用 COUNT(*)=0 时如果没有先按用户分组会出错"],
    ),
    dict(
        id="q5",
        order=5,
        dataset="shop",
        level="入门",
        topic="NULL 处理",
        title="缺少收货城市订单",
        question="履约团队要排查无法按城市分仓的订单，请输出 order_id、user_id、address_city、remark，只看 address_city 为 NULL 的订单，按 order_id 升序。",
        hint="NULL 只能用 IS NULL 判断，不能用等号。",
        answer="""
SELECT order_id, user_id, address_city, remark
FROM orders
WHERE address_city IS NULL
ORDER BY order_id ASC;
""",
        ordered=True,
        explain="NULL 表示未知值，和空字符串不是同一含义。SQL 三值逻辑下 address_city = NULL 永远不会为 true，因此必须使用 IS NULL。MySQL 8 同样如此，如果要兜底展示可用 COALESCE，但筛选不能写等号 NULL。",
        pitfalls=["写 address_city = NULL 会返回 0 行", "把 NULL 当空字符串会漏掉真实缺失值", "未排序时抽样排查顺序不稳定"],
    ),
    dict(
        id="q6",
        order=6,
        dataset="logistics",
        level="入门",
        topic="基础过滤",
        title="异常运单清单",
        question="物流值班同学要看当前异常运单，请输出 shipment_id、warehouse_id、courier_id、last_event_time，筛选 status='EXCEPTION'，按 last_event_time 倒序、shipment_id 倒序。",
        hint="状态是运单当前状态，不需要扫描轨迹表。",
        answer="""
SELECT shipment_id, warehouse_id, courier_id, last_event_time
FROM shipments
WHERE status = 'EXCEPTION'
ORDER BY last_event_time DESC, shipment_id DESC;
""",
        ordered=True,
        explain="如果只看当前异常，运单主表的 status 是读模型，避免每次从高写入轨迹表聚合最新事件。排序按最近变化优先，shipment_id 兜底。MySQL 8 写法一致，线上通常还会配 status,last_event_time 联合索引。",
        pitfalls=["误扫 tracking_events 会放大查询成本", "只按时间排序在同秒事件下不稳定", "把历史 EXCEPTION 事件当当前状态会产生误报"],
    ),
    dict(
        id="q7",
        order=7,
        dataset="logistics",
        level="入门",
        topic="多表 JOIN",
        title="仓库发货量",
        question="仓配负责人要看各仓库创建的运单量，请输出 warehouse_id、warehouse_name、shipment_count，按 shipment_count 倒序、warehouse_id 升序排序。",
        hint="warehouses JOIN shipments 后按仓库聚合。",
        answer="""
SELECT w.warehouse_id, w.warehouse_name, COUNT(s.shipment_id) AS shipment_count
FROM warehouses w
JOIN shipments s ON s.warehouse_id = w.warehouse_id
GROUP BY w.warehouse_id, w.warehouse_name
ORDER BY shipment_count DESC, w.warehouse_id ASC;
""",
        ordered=True,
        explain="仓库维度的发货量来自运单事实表，仓库名来自维表。按仓库主键聚合可以避免同名仓库合并，COUNT(s.shipment_id) 统计匹配运单。MySQL 8 写法一致；如果要保留零发货仓库，应改 LEFT JOIN。",
        pitfalls=["按 warehouse_name 分组可能合并同名仓", "COUNT(*) 配 LEFT JOIN 时会把无运单仓库算成 1", "不补唯一排序会导致并列时顺序不稳定"],
    ),
    dict(
        id="q8",
        order=8,
        dataset="shop",
        level="入门",
        topic="去重计数",
        title="每月下单用户数",
        question="运营要看 2026 上半年每月有多少不同用户下过单，请输出 month、buyer_count，month 格式为 YYYY-MM，按 month 升序排序。",
        hint="月份可用 DATE_FORMAT，用户数用 COUNT(DISTINCT user_id)。",
        answer="""
SELECT DATE_FORMAT(order_time, '%Y-%m') AS month,
       COUNT(DISTINCT user_id) AS buyer_count
FROM orders
WHERE order_time >= '2026-01-01 00:00:00'
  AND order_time < '2026-07-01 00:00:00'
GROUP BY DATE_FORMAT(order_time, '%Y-%m')
ORDER BY month ASC;
""",
        ordered=True,
        explain="业务口径是不同用户数，不是订单数，因此必须 COUNT(DISTINCT user_id)。月份格式化只用于分组展示，过滤仍用原始时间半开区间控制扫描范围。MySQL 8 可直接使用 DATE_FORMAT；SQLite 这里由题目环境补齐该函数，也可用 strftime('%Y-%m', order_time)。",
        pitfalls=["COUNT(*) 会把同一用户同月多单重复计算", "WHERE 中对 order_time 做函数会影响索引", "月份没有补零会导致字符串排序错误"],
    ),
    dict(
        id="q9",
        order=9,
        dataset="shop",
        level="中等",
        topic="GROUP BY HAVING",
        title="高客单价商家",
        question="平台要找 2026 上半年已支付订单客单价不低于 250 且订单数不少于 5 的商家，请输出 merchant_id、merchant_name、paid_orders、avg_amount，平均金额保留 2 位小数，按 avg_amount 倒序、merchant_id 升序。",
        hint="聚合后用 HAVING 过滤订单数和平均值。",
        answer="""
SELECT m.merchant_id, m.merchant_name,
       COUNT(*) AS paid_orders,
       ROUND(AVG(o.total_amount), 2) AS avg_amount
FROM merchants m
JOIN orders o ON o.merchant_id = m.merchant_id
WHERE o.paid_at IS NOT NULL
  AND o.status <> 'CANCELED'
  AND o.order_time >= '2026-01-01 00:00:00'
  AND o.order_time < '2026-07-01 00:00:00'
GROUP BY m.merchant_id, m.merchant_name
HAVING COUNT(*) >= 5 AND AVG(o.total_amount) >= 250
ORDER BY avg_amount DESC, m.merchant_id ASC;
""",
        ordered=True,
        explain="WHERE 先限定可参与成交口径的明细行，HAVING 再过滤聚合后的订单数和均值。平均金额保留两位用于展示，过滤仍使用未 ROUND 的 AVG，避免边界误差。MySQL 8 写法一致，别名在 HAVING 中可用但跨库可移植性略差。",
        pitfalls=["把 COUNT 条件写在 WHERE 会语法错误", "先 ROUND 再比较可能造成边界误判", "未排除取消单会拉低或污染客单价"],
    ),
    dict(
        id="q10",
        order=10,
        dataset="shop",
        level="中等",
        topic="条件聚合",
        title="支付方式成功退款统计",
        question="支付产品要比较各支付方式的成功支付和退款金额，请输出 pay_method、success_amount、refund_amount、refund_rate，金额和比例都保留 2 位小数，按 pay_method 升序。",
        hint="用 SUM(CASE WHEN ...) 做条件聚合，比例要乘 1.0。",
        answer="""
SELECT pay_method,
       ROUND(SUM(CASE WHEN status IN ('SUCCESS', 'REFUNDED') THEN amount ELSE 0 END), 2) AS success_amount,
       ROUND(SUM(CASE WHEN status = 'REFUNDED' THEN amount ELSE 0 END), 2) AS refund_amount,
       ROUND(SUM(CASE WHEN status = 'REFUNDED' THEN amount ELSE 0 END) * 1.0 /
             NULLIF(SUM(CASE WHEN status IN ('SUCCESS', 'REFUNDED') THEN amount ELSE 0 END), 0), 2) AS refund_rate
FROM payments
GROUP BY pay_method
ORDER BY pay_method ASC;
""",
        ordered=True,
        explain="支付方式是同一张流水表中的维度，成功和退款口径属于同组内不同条件，因此条件聚合比多次扫描更直接。比例用 *1.0 避免整数除法，用 NULLIF 防止分母为 0。MySQL 8 可用同样写法，也可用 IF(status=..., amount, 0)。",
        pitfalls=["整数相除会得到 0 或 1", "分母为 0 时不兜底会报错或得到异常值", "把 REFUNDED 排除在成功金额外会让退款率口径不一致"],
    ),
    dict(
        id="q11",
        order=11,
        dataset="shop",
        level="中等",
        topic="EXISTS",
        title="买过退款商品的用户",
        question="客服要定位发生过商品级退款的用户，请输出 user_id、user_name，要求用户至少有一个订单明细 refund_quantity>0，按 user_id 升序。",
        hint="用 EXISTS 表达半连接，避免同一用户多条退款明细导致重复。",
        answer="""
SELECT u.user_id, u.user_name
FROM users u
WHERE EXISTS (
  SELECT 1
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.user_id = u.user_id
    AND oi.refund_quantity > 0
)
ORDER BY u.user_id ASC;
""",
        ordered=True,
        explain="业务只关心用户是否发生过退款，不关心退款明细数量。EXISTS 找到第一条匹配即可成立，天然去重，避免 JOIN 后再 DISTINCT 的额外排序或哈希成本。MySQL 8 优化器通常会把 EXISTS 改写成半连接。",
        pitfalls=["直接 JOIN 不 DISTINCT 会输出重复用户", "只看订单 status='REFUNDED' 可能漏商品级部分退款", "把外层用户条件漏掉会让所有用户都成立"],
    ),
    dict(
        id="q12",
        order=12,
        dataset="shop",
        level="中等",
        topic="NOT EXISTS",
        title="没有成功支付的注册用户",
        question="增长团队要找注册后从未产生成功支付流水的用户，请输出 user_id、user_name、channel，按 channel 升序、user_id 升序。",
        hint="NOT EXISTS 比 NOT IN 更能避开 NULL 陷阱。",
        answer="""
SELECT u.user_id, u.user_name, u.channel
FROM users u
WHERE NOT EXISTS (
  SELECT 1
  FROM orders o
  JOIN payments p ON p.order_id = o.order_id
  WHERE o.user_id = u.user_id
    AND p.status IN ('SUCCESS', 'REFUNDED')
)
ORDER BY u.channel ASC, u.user_id ASC;
""",
        ordered=True,
        explain="这里的约束是没有任何成功支付流水，而不是没有订单。NOT EXISTS 对每个用户做反半连接，遇到 NULL 不会像 NOT IN 那样整体变 UNKNOWN。MySQL 8 写法一致，通常会利用 orders(user_id) 与 payments(order_id,status) 之类索引。",
        pitfalls=["用 NOT IN 且子查询出现 NULL 时可能返回 0 行", "只查 orders 会把未支付取消单误判为成交", "LEFT JOIN 后在 WHERE 写支付状态会破坏反连接口径"],
    ),
    dict(
        id="q13",
        order=13,
        dataset="shop",
        level="中等",
        topic="自连接",
        title="推荐人与被推荐人",
        question="用户运营想看有推荐关系的账号，请输出 user_id、user_name、referrer_name、register_time，按 referrer_name 升序、user_id 升序。",
        hint="users 表自连接，左边是被推荐人，右边是推荐人。",
        answer="""
SELECT u.user_id, u.user_name, r.user_name AS referrer_name, u.register_time
FROM users u
JOIN users r ON r.user_id = u.referrer_user_id
ORDER BY referrer_name ASC, u.user_id ASC;
""",
        ordered=True,
        explain="推荐关系是同一实体表内的父子关系，使用自连接可把 referrer_user_id 翻译成推荐人名称。JOIN 只保留有推荐人的用户，如果业务要看全部用户才改 LEFT JOIN。MySQL 8 写法一致，线上应保证 referrer_user_id 有索引或外键约束。",
        pitfalls=["把连接方向写反会把推荐人与被推荐人颠倒", "用 LEFT JOIN 又不处理 NULL 会混入无推荐人用户", "只输出 referrer_user_id 不利于业务核对"],
    ),
    dict(
        id="q14",
        order=14,
        dataset="shop",
        level="中等",
        topic="窗口函数 ROW_NUMBER",
        title="每个商家销售额 Top2 商品",
        question="商家运营要看每个商家按销售额排名前 2 的商品，请输出 merchant_id、product_id、product_name、sales_amount、rn，按 merchant_id、rn、product_id 升序。",
        hint="先按商品聚合，再用 ROW_NUMBER 按商家分组排序。",
        answer="""
WITH product_sales AS (
  SELECT p.merchant_id, p.product_id, p.product_name,
         SUM(oi.item_amount) AS sales_amount
  FROM products p
  JOIN order_items oi ON oi.product_id = p.product_id
  GROUP BY p.merchant_id, p.product_id, p.product_name
), ranked AS (
  SELECT product_sales.*,
         ROW_NUMBER() OVER (PARTITION BY merchant_id ORDER BY sales_amount DESC, product_id ASC) AS rn
  FROM product_sales
)
SELECT merchant_id, product_id, product_name, ROUND(sales_amount, 2) AS sales_amount, rn
FROM ranked
WHERE rn <= 2
ORDER BY merchant_id ASC, rn ASC, product_id ASC;
""",
        ordered=True,
        explain="TopN 的机制是先把明细压到商品粒度，再在商家分区内排序编号。如果直接对明细行 ROW_NUMBER，会选出订单明细而不是商品。ORDER BY 中 product_id 是并列兜底。MySQL 8 支持相同窗口函数语法。",
        pitfalls=["未先聚合会得到明细 TopN", "窗口排序没有并列兜底会导致结果抖动", "WHERE 不能直接引用同层窗口函数别名，需套 CTE"],
    ),
    dict(
        id="q15",
        order=15,
        dataset="shop",
        level="中等",
        topic="窗口函数 RANK",
        title="订单金额并列排名",
        question="财务要查看订单金额排名，金额相同要并列，请输出 order_id、total_amount、amount_rank，只看非取消订单，按 amount_rank 升序、order_id 升序取前 15。",
        hint="并列排名用 RANK，不要用 ROW_NUMBER。",
        answer="""
SELECT order_id, total_amount,
       RANK() OVER (ORDER BY total_amount DESC) AS amount_rank
FROM orders
WHERE status <> 'CANCELED'
ORDER BY amount_rank ASC, order_id ASC
LIMIT 15;
""",
        ordered=True,
        explain="业务要求金额相同并列，RANK 会给相同 total_amount 相同名次，并在后续名次留下空位；ROW_NUMBER 会强行打散并列。外层 ORDER BY 加 order_id 只影响展示，不改变 RANK 计算。MySQL 8 写法一致。",
        pitfalls=["ROW_NUMBER 不满足并列语义", "DENSE_RANK 不留名次空位，口径不同", "窗口 ORDER BY 和最终展示 ORDER BY 是两件事"],
    ),
    dict(
        id="q16",
        order=16,
        dataset="shop",
        level="中等",
        topic="LAG 环比",
        title="月销售额环比",
        question="经营分析要看每月成交金额及上月环比增幅，请输出 month、gmv、prev_gmv、mom_rate，金额和比例保留 2 位小数，按 month 升序。",
        hint="先月度聚合，再 LAG 取上一月。",
        answer="""
WITH monthly AS (
  SELECT DATE_FORMAT(order_time, '%Y-%m') AS month,
         SUM(total_amount) AS gmv
  FROM orders
  WHERE paid_at IS NOT NULL
    AND status <> 'CANCELED'
  GROUP BY DATE_FORMAT(order_time, '%Y-%m')
)
SELECT month,
       ROUND(gmv, 2) AS gmv,
       ROUND(LAG(gmv) OVER (ORDER BY month), 2) AS prev_gmv,
       ROUND((gmv - LAG(gmv) OVER (ORDER BY month)) * 1.0 /
             NULLIF(LAG(gmv) OVER (ORDER BY month), 0), 2) AS mom_rate
FROM monthly
ORDER BY month ASC;
""",
        ordered=True,
        explain="环比必须先把订单聚合到月粒度，否则 LAG 取到的是上一笔订单。首月没有上一月，因此 prev_gmv 和 mom_rate 为 NULL。比例用 NULLIF 防止除零。MySQL 8 支持 LAG；也可把窗口结果再套一层减少重复表达式。",
        pitfalls=["在订单明细层直接 LAG 会错位", "整数除法或未乘 1.0 会丢小数", "首月没有上一月，不应强行填 0 后计算"],
    ),
    dict(
        id="q17",
        order=17,
        dataset="shop",
        level="中等",
        topic="累计和",
        title="商家月累计成交额",
        question="商家侧看板要展示每个商家 2026 上半年逐月累计成交额，请输出 merchant_id、month、monthly_amount、running_amount，金额保留 2 位小数，按 merchant_id、month 排序。",
        hint="月度聚合后，窗口 SUM 按商家分区按月份累加。",
        answer="""
WITH monthly AS (
  SELECT merchant_id,
         DATE_FORMAT(order_time, '%Y-%m') AS month,
         SUM(total_amount) AS monthly_amount
  FROM orders
  WHERE paid_at IS NOT NULL
    AND status <> 'CANCELED'
  GROUP BY merchant_id, DATE_FORMAT(order_time, '%Y-%m')
)
SELECT merchant_id, month,
       ROUND(monthly_amount, 2) AS monthly_amount,
       ROUND(SUM(monthly_amount) OVER (
         PARTITION BY merchant_id ORDER BY month
         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ), 2) AS running_amount
FROM monthly
ORDER BY merchant_id ASC, month ASC;
""",
        ordered=True,
        explain="累计值的约束是同一商家内按月份顺序累加，所以窗口函数要 PARTITION BY merchant_id。ROWS 框架明确按行累计，避免 RANGE 在并列排序键下产生意外同组。MySQL 8 支持相同窗口框架。",
        pitfalls=["不分区会把不同商家的金额累在一起", "未先聚合到月会输出订单级累计", "缺少 ROWS 框架时不同数据库默认行为不易讲清"],
    ),
    dict(
        id="q18",
        order=18,
        dataset="logistics",
        level="中等",
        topic="移动平均",
        title="仓库近三日发货移动平均",
        question="仓配负责人要看各仓库每天发货量及近 3 个有发货日期的移动平均，请输出 warehouse_id、ship_day、ship_count、ma3，ma3 保留 2 位小数，按 warehouse_id、ship_day。",
        hint="先按仓库和日期聚合，再对聚合结果做 2 PRECEDING 到 CURRENT ROW 的窗口平均。",
        answer="""
WITH daily AS (
  SELECT warehouse_id,
         substr(created_at, 1, 10) AS ship_day,
         COUNT(*) AS ship_count
  FROM shipments
  GROUP BY warehouse_id, substr(created_at, 1, 10)
)
SELECT warehouse_id, ship_day, ship_count,
       ROUND(AVG(ship_count) OVER (
         PARTITION BY warehouse_id ORDER BY ship_day
         ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
       ), 2) AS ma3
FROM daily
ORDER BY warehouse_id ASC, ship_day ASC;
""",
        ordered=True,
        explain="移动平均不能在运单明细层直接 AVG，否则得到的是行级平均。先聚合为每日发货量，再在仓库分区内取当前行和前两行。这里是近 3 个有数据日期，不补零日期。MySQL 8 可用 DATE(created_at) 或生成日历表补齐自然日。",
        pitfalls=["明细层开窗会把每票运单当一天", "未分区会跨仓库计算", "如果业务要自然日补零，需要先补日历表"],
    ),
    dict(
        id="q19",
        order=19,
        dataset="logistics",
        level="中等",
        topic="最新状态",
        title="轨迹表最新事件",
        question="客服要从轨迹表读取每个运单最新一条事件，请输出 shipment_id、event_time、event_type、event_city，按 shipment_id 升序。遇到同一时间多事件时 event_id 大的算最新。",
        hint="ROW_NUMBER 按 shipment_id 分区，event_time 和 event_id 都倒序。",
        answer="""
WITH ranked AS (
  SELECT shipment_id, event_time, event_type, event_city,
         ROW_NUMBER() OVER (PARTITION BY shipment_id ORDER BY event_time DESC, event_id DESC) AS rn
  FROM tracking_events
)
SELECT shipment_id, event_time, event_type, event_city
FROM ranked
WHERE rn = 1
ORDER BY shipment_id ASC;
""",
        ordered=True,
        explain="轨迹事件有乱序和重复，最新状态不能简单取 MAX(event_type)。先按运单分区，再按事件时间和自增 event_id 倒序选第 1 条，可以处理同秒重复上报。MySQL 8 支持 ROW_NUMBER；老版本可用自连接反连接实现。",
        pitfalls=["只 GROUP BY shipment_id, MAX(event_time) 会丢失对应事件类型", "不加 event_id 兜底会在同秒重复时不稳定", "用运单主表 status 无法验证轨迹表最新事件"],
    ),
    dict(
        id="q20",
        order=20,
        dataset="logistics",
        level="中等",
        topic="时效统计",
        title="签收耗时统计",
        question="履约团队要按仓库统计已签收运单的平均签收耗时和超时票数，请输出 warehouse_id、delivered_count、avg_hours、late_count，avg_hours 保留 2 位小数，按 warehouse_id。",
        hint="用 UNIX_TIMESTAMP(delivered_at)-UNIX_TIMESTAMP(shipped_at) 换算小时。",
        answer="""
SELECT warehouse_id,
       COUNT(*) AS delivered_count,
       ROUND(AVG((UNIX_TIMESTAMP(delivered_at) - UNIX_TIMESTAMP(shipped_at)) / 3600.0), 2) AS avg_hours,
       SUM(CASE WHEN (UNIX_TIMESTAMP(delivered_at) - UNIX_TIMESTAMP(shipped_at)) / 3600.0 > promised_hours THEN 1 ELSE 0 END) AS late_count
FROM shipments
WHERE delivered_at IS NOT NULL
  AND shipped_at IS NOT NULL
GROUP BY warehouse_id
ORDER BY warehouse_id ASC;
""",
        ordered=True,
        explain="签收耗时必须同时具备发货和签收时间，未签收运单不能参与平均值。时间差用秒转小时并除以 3600.0 保留小数，超时按 promised_hours 条件聚合。MySQL 8 可用 TIMESTAMPDIFF(HOUR, shipped_at, delivered_at) 或秒级 TIMESTAMPDIFF(SECOND)/3600。",
        pitfalls=["把未签收 NULL 当 0 会严重拉低平均值", "用日期 DATEDIFF 只能得到天数，粒度太粗", "整数除法会丢失小时小数"],
    ),
    dict(
        id="q21",
        order=21,
        dataset="logistics",
        level="中等",
        topic="库存对账",
        title="库存盘点差异",
        question="仓库要核对系统库存与盘点库存差异，请输出 warehouse_id、product_sku、book_qty、checked_qty、diff_qty，只看差异不为 0，按 ABS(diff_qty) 倒序、warehouse_id、product_sku。",
        hint="账面库存可用 available+locked-damaged，再与盘点数量相减。",
        answer="""
SELECT i.warehouse_id, i.product_sku,
       (i.available_qty + i.locked_qty - i.damaged_qty) AS book_qty,
       c.checked_qty,
       (c.checked_qty - (i.available_qty + i.locked_qty - i.damaged_qty)) AS diff_qty
FROM inventory i
JOIN inventory_checks c
  ON c.warehouse_id = i.warehouse_id
 AND c.product_sku = i.product_sku
WHERE (c.checked_qty - (i.available_qty + i.locked_qty - i.damaged_qty)) <> 0
ORDER BY ABS(diff_qty) DESC, i.warehouse_id ASC, i.product_sku ASC;
""",
        ordered=True,
        explain="库存对账要明确账面口径：可售加锁定减残损。盘点表按仓库和 SKU 与库存表连接，差异为盘点减账面，正数代表盘盈。ORDER BY ABS(diff_qty) 优先处理差异大的项。MySQL 8 写法一致，但某些数据库不允许 WHERE 引用别名，所以这里重复表达式。",
        pitfalls=["只比较 available_qty 会漏锁定和残损", "连接条件漏 product_sku 会产生笛卡尔放大", "WHERE 里用 diff_qty 别名在部分数据库不可用"],
    ),
    dict(
        id="q22",
        order=22,
        dataset="shop",
        level="中等",
        topic="LEFT JOIN 条件位置",
        title="用户六月成功支付次数",
        question="用户运营要看所有用户在 2026 年 6 月的成功支付订单数，包括 0 次用户，请输出 user_id、user_name、paid_orders，按 paid_orders 倒序、user_id 升序。",
        hint="右表过滤条件要放在 ON 或条件聚合里，不能放 WHERE。",
        answer="""
SELECT u.user_id, u.user_name,
       COUNT(o.order_id) AS paid_orders
FROM users u
LEFT JOIN orders o
  ON o.user_id = u.user_id
 AND o.paid_at IS NOT NULL
 AND o.status <> 'CANCELED'
 AND o.order_time >= '2026-06-01 00:00:00'
 AND o.order_time < '2026-07-01 00:00:00'
GROUP BY u.user_id, u.user_name
ORDER BY paid_orders DESC, u.user_id ASC;
""",
        ordered=True,
        explain="主体是所有用户，必须保留 0 次用户。把订单过滤条件放 ON 子句中，只影响右表匹配，不会过滤掉左表用户；如果放 WHERE，NULL 扩展行会被过滤，LEFT JOIN 退化为 INNER JOIN。MySQL 8 写法一致。",
        pitfalls=["在 WHERE 写 o.status 会丢掉 0 次用户", "COUNT(*) 会把无订单用户计为 1", "只按 paid_orders 排序时并列用户顺序不稳定"],
    ),
    dict(
        id="q23",
        order=23,
        dataset="shop",
        level="困难",
        topic="CTE 留存率",
        title="注册次月下单留存",
        question="增长分析要看各注册月份用户在次月是否下单留存，请输出 register_month、new_users、retained_users、retention_rate，比例保留 2 位小数，按 register_month 升序。",
        hint="先取用户注册月，再判断是否存在次月订单。SQLite 可用 date(register_month || '-01','+1 month')。",
        answer="""
WITH cohorts AS (
  SELECT user_id, DATE_FORMAT(register_time, '%Y-%m') AS register_month
  FROM users
), retained AS (
  SELECT c.register_month, c.user_id,
         CASE WHEN EXISTS (
           SELECT 1
           FROM orders o
           WHERE o.user_id = c.user_id
             AND o.order_time >= date(c.register_month || '-01', '+1 month')
             AND o.order_time < date(c.register_month || '-01', '+2 month')
         ) THEN 1 ELSE 0 END AS is_retained
  FROM cohorts c
)
SELECT register_month,
       COUNT(*) AS new_users,
       SUM(is_retained) AS retained_users,
       ROUND(SUM(is_retained) * 1.0 / COUNT(*), 2) AS retention_rate
FROM retained
GROUP BY register_month
ORDER BY register_month ASC;
""",
        ordered=True,
        explain="留存的约束是以注册月为 cohort，观察窗口是次月自然月。CTE 先固定 cohort，再用 EXISTS 判断每个用户是否在窗口内下单，最后聚合成比例。SQLite 用 date 字符串函数加月；MySQL 8 可写 DATE_ADD(STR_TO_DATE(CONCAT(register_month,'-01'),'%Y-%m-%d'), INTERVAL 1 MONTH)。",
        pitfalls=["用订单月分组会变成活跃用户统计，不是注册 cohort", "观察窗口不半开会在月底边界重复", "分母应是注册用户数，不是下单用户数"],
    ),
    dict(
        id="q24",
        order=24,
        dataset="shop",
        level="困难",
        topic="漏斗转化",
        title="用户下单到支付漏斗",
        question="产品经理要看各渠道注册用户的下单和支付漏斗，请输出 channel、registered_users、ordered_users、paid_users、order_rate、pay_rate，比例保留 2 位小数，按 channel 升序。",
        hint="以用户为粒度打是否下单、是否支付标记，再按渠道汇总。",
        answer="""
WITH user_flags AS (
  SELECT u.user_id, u.channel,
         CASE WHEN EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.user_id) THEN 1 ELSE 0 END AS has_order,
         CASE WHEN EXISTS (
           SELECT 1
           FROM orders o
           JOIN payments p ON p.order_id = o.order_id
           WHERE o.user_id = u.user_id
             AND p.status IN ('SUCCESS', 'REFUNDED')
         ) THEN 1 ELSE 0 END AS has_paid
  FROM users u
)
SELECT channel,
       COUNT(*) AS registered_users,
       SUM(has_order) AS ordered_users,
       SUM(has_paid) AS paid_users,
       ROUND(SUM(has_order) * 1.0 / COUNT(*), 2) AS order_rate,
       ROUND(SUM(has_paid) * 1.0 / NULLIF(SUM(has_order), 0), 2) AS pay_rate
FROM user_flags
GROUP BY channel
ORDER BY channel ASC;
""",
        ordered=True,
        explain="漏斗必须先统一到用户粒度，否则同一用户多单会把转化人数放大。下单率分母是注册用户，支付率分母通常是已下单用户，两个分母不同。MySQL 8 写法一致，线上可用宽表或物化视图降低 EXISTS 成本。",
        pitfalls=["直接 COUNT(orders) 会把多单用户重复计数", "支付率分母写成注册用户会改变业务口径", "未处理分母为 0 会产生异常比例"],
    ),
    dict(
        id="q25",
        order=25,
        dataset="shop",
        level="困难",
        topic="递归 CTE",
        title="生成六月日期补零成交",
        question="经营看板要显示 2026-06-01 到 2026-06-30 每天成交订单数，没成交的日期也要显示 0，请输出 day、paid_orders，按 day 升序。",
        hint="递归 CTE 生成日历，再 LEFT JOIN 每日聚合。",
        answer="""
WITH RECURSIVE calendar(day) AS (
  SELECT '2026-06-01'
  UNION ALL
  SELECT date(day, '+1 day') FROM calendar WHERE day < '2026-06-30'
), daily AS (
  SELECT substr(order_time, 1, 10) AS day, COUNT(*) AS paid_orders
  FROM orders
  WHERE paid_at IS NOT NULL
    AND status <> 'CANCELED'
    AND order_time >= '2026-06-01 00:00:00'
    AND order_time < '2026-07-01 00:00:00'
  GROUP BY substr(order_time, 1, 10)
)
SELECT c.day, COALESCE(d.paid_orders, 0) AS paid_orders
FROM calendar c
LEFT JOIN daily d ON d.day = c.day
ORDER BY c.day ASC;
""",
        ordered=True,
        explain="趋势图需要连续日期，事实表只包含有订单的日期，因此必须先生成日历维度再 LEFT JOIN 聚合结果。COALESCE 把无匹配日期补 0。SQLite 支持递归 CTE；MySQL 8 也支持 WITH RECURSIVE，但日期加法写 DATE_ADD(day, INTERVAL 1 DAY)。",
        pitfalls=["只从 orders 分组会缺少 0 成交日期", "递归终止条件写错会多一天或死循环", "WHERE 过滤右表会破坏 LEFT JOIN 补零"],
    ),
    dict(
        id="q26",
        order=26,
        dataset="shop",
        level="困难",
        topic="连续 N 天",
        title="连续下单用户",
        question="运营要找 2026 上半年至少连续 2 天都有下单的用户，请输出 user_id、start_day、end_day、day_count，按 user_id、start_day 排序。",
        hint="先按用户去重到天，再用 julianday(day)-ROW_NUMBER 分组识别连续段。",
        answer="""
WITH user_days AS (
  SELECT DISTINCT user_id, substr(order_time, 1, 10) AS day
  FROM orders
  WHERE order_time >= '2026-01-01 00:00:00'
    AND order_time < '2026-07-01 00:00:00'
), marked AS (
  SELECT user_id, day,
         julianday(day) - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day) AS grp
  FROM user_days
), streaks AS (
  SELECT user_id, MIN(day) AS start_day, MAX(day) AS end_day, COUNT(*) AS day_count
  FROM marked
  GROUP BY user_id, grp
)
SELECT user_id, start_day, end_day, day_count
FROM streaks
WHERE day_count >= 2
ORDER BY user_id ASC, start_day ASC;
""",
        ordered=True,
        explain="连续天数要先把同一天多单去重，否则一天多单会伪造成连续。对有序日期减去行号，连续日期会落在同一差值组，再按组聚合。MySQL 8 可用 TO_DAYS(day)-ROW_NUMBER() 实现同样分组。",
        pitfalls=["不 DISTINCT 会让同一天多单破坏行号", "直接比较相邻订单可能跨越同一天重复", "只找固定两天会漏更长连续段"],
    ),
    dict(
        id="q27",
        order=27,
        dataset="logistics",
        level="困难",
        topic="乱序轨迹去重",
        title="去重后轨迹步骤数",
        question="物流研发要评估每个运单去掉重复事件后的有效轨迹步骤数和最新事件，请输出 shipment_id、distinct_steps、latest_event_time、latest_event_type，按 distinct_steps 倒序、shipment_id 升序取前 20。",
        hint="先按 shipment_id、event_type、event_time 去重，再对去重结果取最新事件。",
        answer="""
WITH dedup AS (
  SELECT shipment_id, event_time, event_type, event_city,
         MIN(event_id) AS keep_event_id
  FROM tracking_events
  GROUP BY shipment_id, event_time, event_type, event_city
), ranked AS (
  SELECT dedup.*,
         COUNT(*) OVER (PARTITION BY shipment_id) AS distinct_steps,
         ROW_NUMBER() OVER (PARTITION BY shipment_id ORDER BY event_time DESC, keep_event_id DESC) AS rn
  FROM dedup
)
SELECT shipment_id, distinct_steps, event_time AS latest_event_time, event_type AS latest_event_type
FROM ranked
WHERE rn = 1
ORDER BY distinct_steps DESC, shipment_id ASC
LIMIT 20;
""",
        ordered=True,
        explain="轨迹表存在重复上报，先按运单、时间、类型、城市去重，保留最小 event_id 作为代表。再在去重后的结果上同时计算步骤数和最新事件，避免重复事件放大步骤数。MySQL 8 支持相同 CTE 与窗口函数。",
        pitfalls=["直接 COUNT(*) 会把重复上报算成多个步骤", "最新事件必须在去重后判断，否则重复补写可能干扰展示", "GROUP BY 后随便选 event_type 会得到非确定结果"],
    ),
    dict(
        id="q28",
        order=28,
        dataset="logistics",
        level="困难",
        topic="异常后恢复",
        title="异常运单是否后续签收",
        question="客服复盘要找出现过 EXCEPTION 事件但之后又 DELIVERED 的运单，请输出 shipment_id、exception_time、delivered_time、recover_hours，recover_hours 保留 2 位小数，按 recover_hours 升序、shipment_id 升序。",
        hint="先取每票最早异常时间，再找异常之后最早签收时间。",
        answer="""
WITH first_exception AS (
  SELECT shipment_id, MIN(event_time) AS exception_time
  FROM tracking_events
  WHERE event_type = 'EXCEPTION'
  GROUP BY shipment_id
), recovered AS (
  SELECT fe.shipment_id, fe.exception_time, MIN(te.event_time) AS delivered_time
  FROM first_exception fe
  JOIN tracking_events te
    ON te.shipment_id = fe.shipment_id
   AND te.event_type = 'DELIVERED'
   AND te.event_time > fe.exception_time
  GROUP BY fe.shipment_id, fe.exception_time
)
SELECT shipment_id, exception_time, delivered_time,
       ROUND((UNIX_TIMESTAMP(delivered_time) - UNIX_TIMESTAMP(exception_time)) / 3600.0, 2) AS recover_hours
FROM recovered
ORDER BY recover_hours ASC, shipment_id ASC;
""",
        ordered=True,
        explain="恢复时效的起点是第一次异常，终点是异常之后第一次签收。JOIN 条件中限定 te.event_time > exception_time，避免把异常前的历史签收误算为恢复。MySQL 8 可用 TIMESTAMPDIFF(SECOND, exception_time, delivered_time)/3600。",
        pitfalls=["只看运单当前状态会漏历史异常", "没有限定签收在异常之后会产生负耗时", "同一票多次异常时要先定义取最早还是最后一次"],
    ),
    dict(
        id="q29",
        order=29,
        dataset="shop",
        level="困难",
        topic="相关子查询",
        title="高于商家均值的订单",
        question="风控要找每个商家内金额高于该商家非取消订单平均值的订单，请输出 merchant_id、order_id、total_amount、merchant_avg，merchant_avg 保留 2 位小数，按 merchant_id、total_amount 倒序、order_id。",
        hint="可先按商家聚合均值，再回连订单表。",
        answer="""
WITH merchant_avg AS (
  SELECT merchant_id, AVG(total_amount) AS avg_amount
  FROM orders
  WHERE status <> 'CANCELED'
  GROUP BY merchant_id
)
SELECT o.merchant_id, o.order_id, o.total_amount,
       ROUND(ma.avg_amount, 2) AS merchant_avg
FROM orders o
JOIN merchant_avg ma ON ma.merchant_id = o.merchant_id
WHERE o.status <> 'CANCELED'
  AND o.total_amount > ma.avg_amount
ORDER BY o.merchant_id ASC, o.total_amount DESC, o.order_id ASC;
""",
        ordered=True,
        explain="比较对象是同商家的平均值，不是全平台平均值。先在 CTE 中固定每个商家的非取消订单均值，再回连订单表筛选高于均值的订单，避免相关子查询重复计算。MySQL 8 同样可用 CTE；优化器也可能物化或合并该 CTE。",
        pitfalls=["用全局 AVG 会丢失商家差异", "均值口径和订单筛选口径不一致会前后矛盾", "把取消单放进均值会污染风控阈值"],
    ),
    dict(
        id="q30",
        order=30,
        dataset="logistics",
        level="困难",
        topic="分层聚合",
        title="仓库承诺达成率分层",
        question="履约负责人要看各仓库已签收运单的承诺达成率，并按达成率分层。请输出 warehouse_id、delivered_count、on_time_count、on_time_rate、rate_level，比例保留 2 位小数，按 on_time_rate 倒序、warehouse_id。",
        hint="先按运单判断是否准时，再按仓库聚合并 CASE 分层。",
        answer="""
WITH delivered AS (
  SELECT warehouse_id,
         CASE WHEN (UNIX_TIMESTAMP(delivered_at) - UNIX_TIMESTAMP(shipped_at)) / 3600.0 <= promised_hours THEN 1 ELSE 0 END AS on_time
  FROM shipments
  WHERE delivered_at IS NOT NULL
    AND shipped_at IS NOT NULL
), agg AS (
  SELECT warehouse_id,
         COUNT(*) AS delivered_count,
         SUM(on_time) AS on_time_count,
         SUM(on_time) * 1.0 / COUNT(*) AS on_time_rate
  FROM delivered
  GROUP BY warehouse_id
)
SELECT warehouse_id, delivered_count, on_time_count,
       ROUND(on_time_rate, 2) AS on_time_rate,
       CASE WHEN on_time_rate >= 0.90 THEN '优秀'
            WHEN on_time_rate >= 0.75 THEN '稳定'
            ELSE '需改进' END AS rate_level
FROM agg
ORDER BY on_time_rate DESC, warehouse_id ASC;
""",
        ordered=True,
        explain="分层前要先在运单粒度判断是否准时，再聚合到仓库，否则平均耗时达标不能代表每票都达标。比例保留两位用于展示，分层用未四舍五入的原始比率更稳定。MySQL 8 可用 TIMESTAMPDIFF(SECOND,...)/3600。",
        pitfalls=["用平均耗时判断达成率会掩盖长尾超时", "先 ROUND 再分层可能边界误判", "未排除未签收运单会让分母口径错误"],
    ),
]


SQL_INDEX = [
    dict(
        id="i1",
        order=1,
        dataset="shop",
        title="订单列表按用户和时间倒序翻页",
        question="订单服务有 5000 万行 orders，用户在个人中心查看自己的订单列表，慢查询表现为先全表扫描 orders，再按 order_time 排序后 LIMIT 20，峰值时 CPU 被排序放大。需要让等值 user_id 在前，时间排序在后，并兼顾状态筛选。",
        query="""
SELECT order_id, order_no, status, total_amount, order_time
FROM orders
WHERE user_id = 3
  AND status <> 'CANCELED'
ORDER BY order_time DESC, order_id DESC
LIMIT 20;
""",
        table="orders",
        answer="""
CREATE INDEX idx_orders_user_time_id ON orders(user_id, order_time DESC, order_id DESC);
""",
        explain="user_id 是高选择性的等值条件，放在联合索引最左侧；order_time DESC, order_id DESC 与 ORDER BY 一致，可以减少排序并快速取 LIMIT。status 是不等值且区分度通常低，不适合放在 user_id 前面；本题先用索引定位用户时间序，再回表过滤状态。不要只建 order_time 单列索引，否则仍要扫描大量用户订单。",
        pitfalls=["把低区分度 status 放第一列会扩大扫描范围", "只建 user_id 单列索引仍可能 filesort", "为每个状态单独建索引会增加写入成本且收益低"],
    ),
    dict(
        id="i2",
        order=2,
        dataset="shop",
        title="支付流水按状态和时间统计",
        question="支付表 payments 预计 2 亿行，财务每小时统计最近一段时间的成功支付金额。当前执行计划扫描 payments 全表并过滤 status、paid_at，导致统计任务与在线写入互相影响。需要联合索引支持等值状态和时间范围。",
        query="""
SELECT pay_method, ROUND(SUM(amount), 2) AS amount_sum
FROM payments
WHERE status = 'SUCCESS'
  AND paid_at >= '2026-06-01 00:00:00'
  AND paid_at < '2026-07-01 00:00:00'
GROUP BY pay_method;
""",
        table="payments",
        answer="""
CREATE INDEX idx_payments_status_paid_method ON payments(status, paid_at, pay_method);
""",
        explain="联合索引遵循等值在前、范围在后：status 精确匹配后再按 paid_at 做范围扫描。pay_method 放在后面可让分组读取的列也在索引中，减少回表机会。amount 未放入索引是因为金额列更新和索引体积成本更高，是否做覆盖要看真实写入压力。不要对 paid_at 使用 DATE() 后再过滤。",
        pitfalls=["paid_at 放第一列会先扫整月所有状态", "WHERE DATE(paid_at) 会让普通时间索引失效", "把所有 SELECT 列都塞进索引会显著放大写入成本"],
    ),
    dict(
        id="i3",
        order=3,
        dataset="logistics",
        title="轨迹表按运单取最新事件",
        question="tracking_events 每天新增上千万行，客服打开运单详情只需要该运单最新轨迹。当前计划扫描 tracking_events 后排序，慢在高写入大表的随机读和临时排序。需要支持 shipment_id 等值和 event_time、event_id 倒序取一条。",
        query="""
SELECT event_id, shipment_id, event_time, event_type, event_city
FROM tracking_events
WHERE shipment_id = 20
ORDER BY event_time DESC, event_id DESC
LIMIT 1;
""",
        table="tracking_events",
        answer="""
CREATE INDEX idx_tracking_shipment_time_id ON tracking_events(shipment_id, event_time DESC, event_id DESC);
""",
        explain="shipment_id 是详情页等值条件，放第一列可以直接定位单票轨迹；event_time DESC、event_id DESC 与排序一致，可从索引头部取最新一条，避免额外排序。event_id 作为同秒事件兜底。不要只建 event_time 索引，因为它不能快速限定某个运单。",
        pitfalls=["只按 event_time 建索引会扫描全局最新事件", "不带 event_id 兜底会在同秒重复轨迹下不稳定", "把 event_type 放第一列不符合详情页查询条件"],
    ),
    dict(
        id="i4",
        order=4,
        dataset="logistics",
        title="运单按仓库状态和创建时间筛选",
        question="履约后台 shipments 有 8000 万行，仓库主管查看本仓异常和在途运单，当前执行计划全表扫描后再按 created_at 排序。查询条件包含 warehouse_id、status 和 created_at 范围，列表只取最近 50 条。",
        query="""
SELECT shipment_id, status, created_at, destination_city
FROM shipments
WHERE warehouse_id = 2
  AND status = 'EXCEPTION'
  AND created_at >= '2026-01-01 00:00:00'
ORDER BY created_at DESC, shipment_id DESC
LIMIT 50;
""",
        table="shipments",
        answer="""
CREATE INDEX idx_shipments_wh_status_created_id ON shipments(warehouse_id, status, created_at DESC, shipment_id DESC);
""",
        explain="warehouse_id 和 status 都是等值过滤，放在 created_at 范围和排序列之前；created_at DESC、shipment_id DESC 与列表排序一致，能减少排序并快速 LIMIT。destination_city 不放入索引，是为了控制索引宽度。不要把 created_at 放第一列，否则会先扫大量仓库和状态。",
        pitfalls=["范围列放在等值列之前会削弱过滤", "只建 status 单列索引区分度低", "为 destination_city 盲目做覆盖会放大索引体积"],
    ),
    dict(
        id="i5",
        order=5,
        dataset="logistics",
        title="库存 SKU 查询覆盖索引",
        question="库存表 inventory 在大促前有上亿批次记录，商品详情页按 warehouse_id 和 product_sku 读取可售、锁定、残损数量。当前计划扫描 inventory 全表，导致热点 SKU 查询抖动。需要让查询通过联合索引精确定位，并尽量覆盖读字段。",
        query="""
SELECT available_qty, locked_qty, damaged_qty
FROM inventory
WHERE warehouse_id = 1
  AND product_sku = 'SKU-B001';
""",
        table="inventory",
        answer="""
CREATE INDEX idx_inventory_wh_sku_qty ON inventory(warehouse_id, product_sku, available_qty, locked_qty, damaged_qty);
""",
        explain="warehouse_id 与 product_sku 都是等值条件，联合索引可直接定位仓内 SKU。把 available_qty、locked_qty、damaged_qty 放到后缀，在支持覆盖扫描的引擎中可以少回表；即使在 SQLite 计划中也会走该索引。不要只建 product_sku，因为同一 SKU 分布在多个仓。",
        pitfalls=["单列 product_sku 会扫描多个仓库", "单列 warehouse_id 会扫描仓内所有 SKU", "覆盖列过多会增加更新库存时的索引维护成本"],
    ),
    dict(
        id="i6",
        order=6,
        dataset="shop",
        title="避免函数过滤导致订单时间索引失效",
        question="订单看板 orders 5000 万行，原慢查询写 DATE_FORMAT(order_time,'%Y-%m')='2026-06'，导致无法按时间范围走索引。目标查询已经改写成半开区间，需要建立能支持 merchant_id 等值和 order_time 范围的索引。",
        query="""
SELECT order_id, total_amount, order_time
FROM orders
WHERE merchant_id = 2
  AND order_time >= '2026-06-01 00:00:00'
  AND order_time < '2026-07-01 00:00:00'
ORDER BY order_time ASC, order_id ASC;
""",
        table="orders",
        answer="""
CREATE INDEX idx_orders_merchant_time_id ON orders(merchant_id, order_time ASC, order_id ASC);
""",
        explain="修复机制有两步：SQL 改为半开时间区间，索引按 merchant_id 等值在前、order_time 范围和排序在后。这样可以在单商家内按时间有序扫描。不要把 DATE_FORMAT 表达式套在列上；如果业务必须按月表达式查询，MySQL 可考虑生成列或函数索引，但写入成本和兼容性要评估。",
        pitfalls=["继续使用 DATE_FORMAT(order_time) 会让普通索引用不上", "只建 merchant_id 会产生范围内排序", "只建 order_time 会扫描所有商家六月订单"],
    ),
]


SQL_SCHEMA = [
    dict(
        id="s1",
        order=1,
        title="订单与支付含部分退款表设计",
        requirement="设计一个电商订单与支付数据模型，支持用户下单、订单多商品明细、一次订单多次支付尝试、部分退款和全额退款。系统要能按用户查订单列表，按订单号查详情，按支付单号对账，按退款状态追踪售后进度。金额必须可审计，订单状态和支付状态要可扩展，不能因为支付回调重复到达而多记账。",
        queries_needed=["按 user_id 和下单时间倒序分页查订单", "按 order_no 查询订单主表、明细、支付流水和退款流水", "按 pay_no 或 refund_no 做幂等回调处理", "按商家和日期统计成交金额、退款金额、净收入", "按订单状态扫描超时未支付订单"],
        reference_ddl="""
CREATE TABLE `orders` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '订单主键',
  `order_no` VARCHAR(64) NOT NULL COMMENT '业务订单号',
  `user_id` BIGINT NOT NULL COMMENT '用户 ID',
  `merchant_id` BIGINT NOT NULL COMMENT '商家 ID',
  `status` VARCHAR(32) NOT NULL COMMENT '订单状态',
  `total_amount` DECIMAL(18,2) NOT NULL COMMENT '订单应付金额',
  `paid_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '已支付金额',
  `refund_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '已退款金额',
  `created_at` DATETIME NOT NULL COMMENT '下单时间',
  `paid_at` DATETIME NULL COMMENT '支付完成时间',
  `deleted_at` DATETIME NULL COMMENT '软删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_user_created` (`user_id`, `created_at`, `id`),
  KEY `idx_merchant_created` (`merchant_id`, `created_at`, `id`),
  KEY `idx_status_created` (`status`, `created_at`, `id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单主表';
CREATE TABLE `order_items` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '明细主键',
  `order_id` BIGINT NOT NULL COMMENT '订单 ID',
  `product_id` BIGINT NOT NULL COMMENT '商品 ID',
  `sku_id` BIGINT NOT NULL COMMENT 'SKU ID',
  `quantity` INT NOT NULL COMMENT '购买数量',
  `unit_price` DECIMAL(18,2) NOT NULL COMMENT '成交单价',
  `refund_quantity` INT NOT NULL DEFAULT 0 COMMENT '已退数量',
  PRIMARY KEY (`id`),
  KEY `idx_order` (`order_id`),
  KEY `idx_sku_order` (`sku_id`, `order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单商品明细';
CREATE TABLE `payments` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '支付主键',
  `pay_no` VARCHAR(64) NOT NULL COMMENT '支付单号',
  `order_id` BIGINT NOT NULL COMMENT '订单 ID',
  `channel` VARCHAR(32) NOT NULL COMMENT '支付渠道',
  `status` VARCHAR(32) NOT NULL COMMENT '支付状态',
  `amount` DECIMAL(18,2) NOT NULL COMMENT '支付金额',
  `paid_at` DATETIME NULL COMMENT '支付时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pay_no` (`pay_no`),
  KEY `idx_order_status` (`order_id`, `status`),
  KEY `idx_status_paid` (`status`, `paid_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付流水';
CREATE TABLE `refunds` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '退款主键',
  `refund_no` VARCHAR(64) NOT NULL COMMENT '退款单号',
  `order_id` BIGINT NOT NULL COMMENT '订单 ID',
  `payment_id` BIGINT NOT NULL COMMENT '支付 ID',
  `status` VARCHAR(32) NOT NULL COMMENT '退款状态',
  `amount` DECIMAL(18,2) NOT NULL COMMENT '退款金额',
  `created_at` DATETIME NOT NULL COMMENT '申请时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_refund_no` (`refund_no`),
  KEY `idx_order_status` (`order_id`, `status`),
  KEY `idx_payment` (`payment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='退款流水';
""",
        explain="订单主表保存稳定的订单级状态和金额快照，订单明细保存商品粒度，支付与退款单独建流水表以支持多次支付尝试和部分退款。order_no、pay_no、refund_no 使用唯一键承担幂等约束，回调重复到达时先按唯一键读当前状态再做状态机推进。金额使用 DECIMAL(18,2) 而不是浮点，时间使用 DATETIME 并保留 created_at、paid_at 等业务时间。用户订单列表用 user_id、created_at 联合索引，商家统计用 merchant_id、created_at。软删除放 deleted_at，但财务表通常只做逻辑隐藏不物理删除。大规模订单可按 user_id 或 merchant_id 加时间做分库分表键，选择时要匹配最高频查询入口。",
        points=["订单、明细、支付、退款分表清晰", "业务单号唯一键保证幂等", "金额使用 DECIMAL 并保存快照", "联合索引匹配用户列表和商家统计", "状态字段可扩展且需状态机约束", "说明软删除和分库分表键取舍"],
    ),
    dict(
        id="s2",
        order=2,
        title="库存与库存流水防超卖设计",
        requirement="设计一个库存系统，支持按仓库和 SKU 管理可售库存、锁定库存、已售库存和残损库存。下单时要先锁库存，支付成功后扣减，取消或超时释放，后台要能按库存流水对账并定位某次库存变更来源。高并发大促下不能超卖，库存扣减必须具备幂等能力。",
        queries_needed=["按 warehouse_id 和 sku_id 查询当前库存", "按 biz_no 幂等处理锁定、扣减、释放请求", "按 SKU 查询一段时间内库存流水", "按仓库聚合低库存商品", "按流水汇总校验当前库存是否一致"],
        reference_ddl="""
CREATE TABLE `stock_items` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '库存主键',
  `warehouse_id` BIGINT NOT NULL COMMENT '仓库 ID',
  `sku_id` BIGINT NOT NULL COMMENT 'SKU ID',
  `available_qty` INT NOT NULL COMMENT '可售库存',
  `locked_qty` INT NOT NULL COMMENT '锁定库存',
  `sold_qty` INT NOT NULL COMMENT '已售库存',
  `damaged_qty` INT NOT NULL COMMENT '残损库存',
  `version` BIGINT NOT NULL COMMENT '乐观锁版本',
  `updated_at` DATETIME NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_wh_sku` (`warehouse_id`, `sku_id`),
  KEY `idx_sku` (`sku_id`),
  KEY `idx_wh_available` (`warehouse_id`, `available_qty`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存余额';
CREATE TABLE `stock_flows` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水主键',
  `biz_no` VARCHAR(64) NOT NULL COMMENT '业务幂等号',
  `stock_item_id` BIGINT NOT NULL COMMENT '库存主键',
  `change_type` VARCHAR(32) NOT NULL COMMENT '变更类型',
  `qty_delta` INT NOT NULL COMMENT '数量变化',
  `before_available` INT NOT NULL COMMENT '变更前可售',
  `after_available` INT NOT NULL COMMENT '变更后可售',
  `created_at` DATETIME NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_biz_type` (`biz_no`, `change_type`),
  KEY `idx_stock_created` (`stock_item_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存流水';
CREATE TABLE `stock_reservations` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '锁定记录主键',
  `reservation_no` VARCHAR(64) NOT NULL COMMENT '锁定单号',
  `stock_item_id` BIGINT NOT NULL COMMENT '库存主键',
  `order_no` VARCHAR(64) NOT NULL COMMENT '订单号',
  `locked_qty` INT NOT NULL COMMENT '锁定数量',
  `status` VARCHAR(32) NOT NULL COMMENT '锁定状态',
  `expire_at` DATETIME NOT NULL COMMENT '过期时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_reservation_no` (`reservation_no`),
  KEY `idx_order` (`order_no`),
  KEY `idx_status_expire` (`status`, `expire_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存锁定记录';
""",
        explain="库存余额表按仓库和 SKU 唯一，承载高频读写；库存流水表记录每次变化前后值和业务幂等号，用于对账和审计；锁定表表达下单后支付前的临时占用。防超卖的核心是原子条件更新，例如 available_qty>=扣减量 时才 update，并配合 version 或数据库行锁。biz_no 加 change_type 唯一键保证重试不会重复扣减。库存数量用整数，不能用浮点；时间字段区分流水创建时间和锁定过期时间。大规模场景可按 sku_id 或 warehouse_id 分片，但要避免同一热点 SKU 被拆到多个主写节点导致一致性复杂化。",
        points=["余额、流水、锁定三类表职责独立", "warehouse_id+sku_id 唯一", "条件更新或乐观锁防超卖", "biz_no 唯一保证幂等", "流水保存前后值便于对账", "低库存和过期锁定索引明确"],
    ),
    dict(
        id="s3",
        order=3,
        title="高写入物流轨迹表设计",
        requirement="设计物流轨迹系统，运单创建后会不断写入揽收、出库、到达、派送、签收、异常等事件。客服需要按运单号快速查看最新状态和完整轨迹，运营需要统计线路时效和异常率。轨迹写入量很高，可能存在重复推送、乱序补写和同一秒多事件，系统要能去重并保留原始事件证据。",
        queries_needed=["按 shipment_no 查询运单当前状态", "按 shipment_id 倒序查询轨迹事件", "按 event_no 幂等写入轨迹", "按仓库和创建时间统计签收时效", "扫描长时间未更新的在途运单"],
        reference_ddl="""
CREATE TABLE `shipments` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '运单主键',
  `shipment_no` VARCHAR(64) NOT NULL COMMENT '运单号',
  `order_no` VARCHAR(64) NOT NULL COMMENT '订单号',
  `warehouse_id` BIGINT NOT NULL COMMENT '发货仓',
  `courier_id` BIGINT NULL COMMENT '配送员',
  `status` VARCHAR(32) NOT NULL COMMENT '当前状态',
  `created_at` DATETIME NOT NULL COMMENT '创建时间',
  `shipped_at` DATETIME NULL COMMENT '发货时间',
  `delivered_at` DATETIME NULL COMMENT '签收时间',
  `last_event_at` DATETIME NULL COMMENT '最新事件时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_shipment_no` (`shipment_no`),
  KEY `idx_order` (`order_no`),
  KEY `idx_wh_created` (`warehouse_id`, `created_at`, `id`),
  KEY `idx_status_last` (`status`, `last_event_at`, `id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运单主表';
CREATE TABLE `tracking_events` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '轨迹主键',
  `event_no` VARCHAR(64) NOT NULL COMMENT '事件幂等号',
  `shipment_id` BIGINT NOT NULL COMMENT '运单 ID',
  `event_type` VARCHAR(32) NOT NULL COMMENT '事件类型',
  `event_time` DATETIME NOT NULL COMMENT '业务事件时间',
  `event_city` VARCHAR(64) NOT NULL COMMENT '事件城市',
  `raw_payload` TEXT NULL COMMENT '原始报文',
  `created_at` DATETIME NOT NULL COMMENT '入库时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_event_no` (`event_no`),
  KEY `idx_shipment_time` (`shipment_id`, `event_time`, `id`),
  KEY `idx_type_time` (`event_type`, `event_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='轨迹事件';
CREATE TABLE `shipment_status_logs` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '状态日志主键',
  `shipment_id` BIGINT NOT NULL COMMENT '运单 ID',
  `from_status` VARCHAR(32) NOT NULL COMMENT '原状态',
  `to_status` VARCHAR(32) NOT NULL COMMENT '新状态',
  `event_id` BIGINT NOT NULL COMMENT '触发事件',
  `created_at` DATETIME NOT NULL COMMENT '变更时间',
  PRIMARY KEY (`id`),
  KEY `idx_shipment_created` (`shipment_id`, `created_at`),
  KEY `idx_to_created` (`to_status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运单状态变更日志';
""",
        explain="运单主表是当前状态读模型，轨迹事件表是追加写事实表，状态日志用于审计状态机推进。高写入轨迹不能每次客服查询都聚合全表最新状态，所以 shipments 冗余 status 和 last_event_at；写入事件时用 event_no 唯一键去重，并按 event_time 与 id 保证乱序和同秒事件可排序。raw_payload 可保存原始报文用于追责，但不要在列表页读取。轨迹查询索引用 shipment_id、event_time、id，异常统计用 event_type、event_time。大规模可按 shipment_id 哈希或按创建月分表，当前状态表和事件表的分片键要便于按运单聚合读取。",
        points=["当前状态读模型与轨迹事实表分离", "event_no 唯一键处理重复推送", "轨迹索引支持按运单有序读取", "保留 raw_payload 但避免热查询读取", "说明乱序和同秒事件排序", "状态日志可审计状态机"],
    ),
    dict(
        id="s4",
        order=4,
        title="商家店铺与多角色权限设计",
        requirement="设计商家工作台的店铺与权限模型。一个商家主体可以开多个店铺，一个用户可以加入多个店铺并拥有店长、运营、客服、财务等角色，不同角色拥有不同菜单和操作权限。系统要支持邀请成员、禁用成员、按店铺查询成员权限，以及审计谁在什么时间修改了商品、订单或结算信息。",
        queries_needed=["按 user_id 查询可访问的店铺和角色", "按 shop_id 查询成员列表", "校验用户是否拥有某个 permission_code", "查询角色绑定的权限清单", "按资源和时间查询操作审计日志"],
        reference_ddl="""
CREATE TABLE `merchants` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '商家主体 ID',
  `merchant_name` VARCHAR(128) NOT NULL COMMENT '商家名称',
  `status` VARCHAR(32) NOT NULL COMMENT '主体状态',
  `created_at` DATETIME NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_status_created` (`status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商家主体';
CREATE TABLE `shops` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '店铺 ID',
  `merchant_id` BIGINT NOT NULL COMMENT '商家主体 ID',
  `shop_name` VARCHAR(128) NOT NULL COMMENT '店铺名称',
  `status` VARCHAR(32) NOT NULL COMMENT '店铺状态',
  `created_at` DATETIME NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_merchant_status` (`merchant_id`, `status`),
  KEY `idx_status_created` (`status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='店铺';
CREATE TABLE `shop_members` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '成员 ID',
  `shop_id` BIGINT NOT NULL COMMENT '店铺 ID',
  `user_id` BIGINT NOT NULL COMMENT '用户 ID',
  `status` VARCHAR(32) NOT NULL COMMENT '成员状态',
  `created_at` DATETIME NOT NULL COMMENT '加入时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_shop_user` (`shop_id`, `user_id`),
  KEY `idx_user_status` (`user_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='店铺成员';
CREATE TABLE `roles` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '角色 ID',
  `role_code` VARCHAR(64) NOT NULL COMMENT '角色编码',
  `role_name` VARCHAR(64) NOT NULL COMMENT '角色名称',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色';
CREATE TABLE `member_roles` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '成员角色 ID',
  `member_id` BIGINT NOT NULL COMMENT '成员 ID',
  `role_id` BIGINT NOT NULL COMMENT '角色 ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_member_role` (`member_id`, `role_id`),
  KEY `idx_role` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成员角色';
CREATE TABLE `permissions` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '权限 ID',
  `permission_code` VARCHAR(128) NOT NULL COMMENT '权限编码',
  `permission_name` VARCHAR(128) NOT NULL COMMENT '权限名称',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_permission_code` (`permission_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限点';
CREATE TABLE `role_permissions` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '角色权限 ID',
  `role_id` BIGINT NOT NULL COMMENT '角色 ID',
  `permission_id` BIGINT NOT NULL COMMENT '权限 ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_permission` (`role_id`, `permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色权限';
CREATE TABLE `operation_audits` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '审计 ID',
  `shop_id` BIGINT NOT NULL COMMENT '店铺 ID',
  `user_id` BIGINT NOT NULL COMMENT '操作人',
  `resource_type` VARCHAR(64) NOT NULL COMMENT '资源类型',
  `resource_id` BIGINT NOT NULL COMMENT '资源 ID',
  `action` VARCHAR(64) NOT NULL COMMENT '动作',
  `created_at` DATETIME NOT NULL COMMENT '操作时间',
  PRIMARY KEY (`id`),
  KEY `idx_shop_user_time` (`shop_id`, `user_id`, `created_at`),
  KEY `idx_resource_time` (`resource_type`, `resource_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作审计';
""",
        explain="商家主体、店铺、成员、角色、权限按 RBAC 拆分，避免把权限数组塞进用户表导致难查询和难审计。shop_members 用 shop_id、user_id 唯一约束保证同一用户在店铺内只有一条成员记录，member_roles 支持多角色叠加。权限校验链路是 user_id 查有效成员，再查角色和权限编码，频繁校验可缓存但数据库仍是准源。审计表独立追加写，按资源和时间建索引用于追溯。状态字段用 VARCHAR 便于扩展，禁用成员保留记录而不是物理删除。若规模很大，可按 merchant_id 或 shop_id 作为分片键，因为大多数查询都在店铺边界内完成。",
        points=["商家主体和店铺分层", "成员与角色多对多", "角色与权限多对多", "唯一键防重复授权", "审计日志独立追加写", "说明缓存与数据库准源关系"],
    ),
    dict(
        id="s5",
        order=5,
        title="优惠券领取与核销一人一张设计",
        requirement="设计优惠券系统，平台创建券活动后，用户可以领取优惠券，一个活动要求同一用户最多领取一张。优惠券有有效期、门槛、面额、总库存和已领数量。下单时需要锁定优惠券，支付成功后核销，订单取消后释放。运营要能统计领取率、核销率和活动成本。",
        queries_needed=["按 coupon_id 查询活动库存和有效期", "按 user_id 查询可用券列表", "按 coupon_id 和 user_id 幂等领取", "按 order_no 查询锁定或核销的券", "按活动统计领取数、核销数和补贴金额"],
        reference_ddl="""
CREATE TABLE `coupons` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '券活动 ID',
  `coupon_name` VARCHAR(128) NOT NULL COMMENT '券名称',
  `coupon_type` VARCHAR(32) NOT NULL COMMENT '券类型',
  `threshold_amount` DECIMAL(18,2) NOT NULL COMMENT '使用门槛',
  `discount_amount` DECIMAL(18,2) NOT NULL COMMENT '优惠金额',
  `total_stock` INT NOT NULL COMMENT '总库存',
  `received_count` INT NOT NULL DEFAULT 0 COMMENT '已领取数',
  `start_at` DATETIME NOT NULL COMMENT '开始时间',
  `end_at` DATETIME NOT NULL COMMENT '结束时间',
  `status` VARCHAR(32) NOT NULL COMMENT '活动状态',
  PRIMARY KEY (`id`),
  KEY `idx_status_time` (`status`, `start_at`, `end_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优惠券活动';
CREATE TABLE `user_coupons` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '用户券 ID',
  `coupon_id` BIGINT NOT NULL COMMENT '券活动 ID',
  `user_id` BIGINT NOT NULL COMMENT '用户 ID',
  `status` VARCHAR(32) NOT NULL COMMENT '用户券状态',
  `received_at` DATETIME NOT NULL COMMENT '领取时间',
  `locked_order_no` VARCHAR(64) NULL COMMENT '锁定订单号',
  `used_order_no` VARCHAR(64) NULL COMMENT '核销订单号',
  `used_at` DATETIME NULL COMMENT '核销时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_coupon_user` (`coupon_id`, `user_id`),
  KEY `idx_user_status` (`user_id`, `status`, `received_at`),
  KEY `idx_order` (`locked_order_no`, `used_order_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户优惠券';
CREATE TABLE `coupon_flows` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水 ID',
  `biz_no` VARCHAR(64) NOT NULL COMMENT '业务幂等号',
  `user_coupon_id` BIGINT NOT NULL COMMENT '用户券 ID',
  `flow_type` VARCHAR(32) NOT NULL COMMENT '流水类型',
  `order_no` VARCHAR(64) NULL COMMENT '关联订单号',
  `amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '优惠金额',
  `created_at` DATETIME NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_biz_type` (`biz_no`, `flow_type`),
  KEY `idx_user_coupon_created` (`user_coupon_id`, `created_at`),
  KEY `idx_order` (`order_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优惠券流水';
""",
        explain="券活动表保存库存、门槛、面额和有效期，用户券表保存每个用户领取后的状态，流水表记录领取、锁定、核销、释放等动作。coupon_id、user_id 唯一键直接满足一人一张，并作为并发领取的数据库兜底；活动库存用条件更新 total_stock>received_count 防止超发。下单锁券先把用户券状态从可用改为锁定并记录 locked_order_no，支付成功再改为已使用，取消则释放。金额使用 DECIMAL，状态使用可扩展字符串。统计领取率和核销率可以从用户券聚合，成本从流水或已核销金额聚合。大促热点券可按 coupon_id 分片或引入库存桶，但唯一领取约束仍要有全局幂等方案。",
        points=["coupon_id+user_id 唯一保证一人一张", "库存条件更新防超发", "用户券状态覆盖可用、锁定、已用、释放", "流水表提供幂等和审计", "金额和有效期类型选择正确", "说明热点券分片和全局幂等取舍"],
    ),
]
