CHAPTER = dict(
    id="mysql",
    order=4,
    name="MySQL",
    blurb="从索引和慢查询入手，讲透 InnoDB 事务、锁与扩展",
    map="""以 MySQL 8.0 的 InnoDB 为准。碰到“为什么慢”，先追问读了多少索引记录、是否回表、有没有排序或锁等待；碰到“为什么读到这个值”，先问隔离级别、是不是同一事务、用的是快照读还是加锁读。

| 板块 | 必会问题 | 一句话答案 |
|---|---|---|
| 索引结构 | 为什么用 B+ 树？ | 多路分支压低树高，叶子有序且相连，既能做点查也能做范围扫描。 |
| 索引访问 | 什么叫回表、覆盖？ | 二级索引用主键去聚簇索引取整行叫回表；所需列都在索引里就具备覆盖条件。 |
| 索引设计 | 联合索引从哪一列开始用？ | 按键元组排序；先找连续左前缀，范围后的列通常不继续收窄扫描区间，但仍可过滤或覆盖查询。 |
| 慢查询 | 从发现到上线怎么排查？ | 聚合慢日志定优先级，用计划和实测找原因，再通过同数据量、同并发对照验证。 |
| 事务 | ACID 和隔离级别分别是什么？ | undo 能撤销，redo 能恢复，锁和 MVCC 保隔离，一致性还要靠约束和业务规则。 |
| 并发 | 为什么有时看到旧值，有时会阻塞？ | 快照读靠 Read View 选历史版本；加锁读针对当前数据，范围扫描还可能锁住间隙。 |
| 日志 | 为什么 redo 和 binlog 都要写？ | 一个供引擎崩溃恢复，一个供复制与时间点恢复；内部两阶段提交协调两者。 |
| 扩展 | 深分页、从库旧读、分片怎么选？ | 分别减少翻页扫描、按一致性要求路由、按常用访问键分片；三者不是同一种性能问题。 |

**复习顺序**：先会画“二级索引 → 主键 → 聚簇索引”，再用一条慢 SQL 练读 `EXPLAIN`；然后开两个连接演练隔离级别、间隙锁和死锁。最后看日志、分页、复制和分片。面试先给结论，再给一条 SQL 或一张时序表，最后说验证指标和取舍。""",
    cards=[
        dict(
            id="mysql-bplus-tree",
            q="为什么 InnoDB 的普通索引用 B+ 树，而不是哈希或二叉树？",
            level=1,
            short="数据库索引要少读页，还要支持范围扫描。B+ 树的内部页只负责导航，一个页能指向很多子页，树比较矮；数据记录或索引条目放在有序叶子页，定位左边界后可以沿叶子向后扫。哈希擅长等值但不保序，平衡二叉树的分支少，经典 B 树的内部节点也存数据条目，B+ 树更容易把内部页用作高扇出的导航。",
            points=[
                "说出数据库按页管理数据，树高影响点查访问的页数",
                "B+ 树内部页负责导航，分支多；叶子有序相连，适合范围与排序",
                "对比哈希不保序、二叉树分支少、经典 B 树内部节点也存数据条目",
                "给出三层容量估算：根扇出 × 中间层扇出 × 每叶页的行数，并说明假设",
            ],
            explain="""### 先算读几页，不只算比较几次
磁盘上的数据不是每次只取几字节的主键。InnoDB 按页管理索引，常见默认页大小是 16 KiB；找不到已缓存的页才要从存储读。把内部页想成一大张目录：只放导航需要的分隔键和子页指针，一个页能指向很多子页。树越矮，一次点查走过的页就越少。常用的根和上层页通常能复用缓存，因此走三层不等于每次做三次磁盘 I/O。

### 三层能装多少行？把假设写出来
以聚簇索引为例，三层指 **根页 → 中间页 → 叶页**。假设内部页平均能挂 600 个子页；行的页内空间约 1 KiB，给页头、目录和填充留余量，假设一个叶页平均能放 12 行。用这个模型，约有 `600 × 600 = 360000` 个叶页，能放 `360000 × 12 = 4320000` 行，即约 430 万行。这里是在估数量级，不是在报容量上限：键长、行格式、页大小、分裂后的填充率都会改变结果。二级索引的叶条目只放相关键值和主键，不能直接套用这个行宽。

### 同一条范围查询怎么走
例如按主键取 1000 到 1100。先从根定位到 1000 附近的叶页，再顺着相邻叶页按序读，到超过 1100 停止，不用为每个 ID 从根重新找起。叶页链表示逻辑顺序，不保证这些页在磁盘上物理连续。

| 结构 | 为什么不是首选 |
|---|---|
| 哈希 | 等值定位快，但桶没有键的全局顺序，不能沿桶完成有序范围扫描。 |
| 平衡二叉树 | 每个节点最多两个孩子，记录数相同时通常比多路树层数多；内存查找和磁盘页访问不是一回事。 |
| 经典 B 树 | 内部节点也存数据条目，点查有机会提前命中，但分支容量可能降低，范围遍历也不像沿叶链那么直接。 |

### 面试怎么说
先说目标是“减少访问页数，同时保住顺序”，再用点查和范围查各走一遍；被问三层容量时先说叶页装的是整行还是二级键，再列假设做乘法。""",
            followups=[
                dict(q="树高三层，就一定读三次磁盘吗？", a="不一定。树高是定位路径上访问的页数，页在 Buffer Pool 时是内存访问；跨叶页扫描或二级索引回表则还可能访问其他页。"),
                dict(q="既然哈希点查快，InnoDB 里就完全没有哈希吗？", a="不能这么说。自适应哈希索引是为部分热点访问建立的内部优化，不是替代 InnoDB 普通 B+ 树索引的建表选项，也不提供有序范围扫描。"),
            ],
            pitfalls=["把估算出的 430 万行当成所有表的固定阈值。", "把叶页逻辑相连说成磁盘地址必然连续。"],
            hook="用同一份造数分别跑主键点查和主键范围查，把数据量逐步放大，记录冷暖缓存下的延迟和专用实例的物理读增量。范围查还要固定返回行数，否则容易把传输开销误认成树高差异。",
            mnemonic="内页管导航，叶页按序排；分支宽，查得浅。",
        ),
        dict(
            id="mysql-clustered-covering",
            q="聚簇索引、二级索引、回表和覆盖索引是什么关系？",
            level=1,
            short="InnoDB 的聚簇索引通常以主键组织，叶子就是行记录；二级索引叶子保存索引列和对应主键。用二级索引先定位主键，再到聚簇索引取缺失列叫回表。如果查询需要的列在二级索引里都能找到，就具备覆盖条件，通常无需为取列回表。主键越宽，多个二级索引也会跟着变大。",
            points=[
                "聚簇索引叶子存行，一张表只有一个；一般优先使用主键",
                "二级索引叶子记录包含索引列和聚簇键，常见情况是主键",
                "用二级键找到主键，再通过聚簇索引取缺失列是回表",
                "用同一张 user 表举出覆盖和回表的两条查询",
            ],
            explain="""### 两棵树分别存什么
把聚簇索引想成按编号排好的一本名册，翻到编号就能看到整条记录。二级索引像姓氏目录：能按名字快速找到一个或多个编号，但不一定附带个人资料。InnoDB 只有一种方式组织同一份聚簇数据，所以每张表只有一个聚簇索引；可以另建多个按不同列排序的二级索引。指定了主键，一般就是用它来组织聚簇索引；二级索引记录的是聚簇键，而不是容易随页移动变化的行物理地址。

### 一张 user 表，走三条路径
```sql
CREATE TABLE `user` (
    id BIGINT PRIMARY KEY,
    email VARCHAR(100) NOT NULL,
    nickname VARCHAR(40) NOT NULL,
    KEY idx_email (email)
) ENGINE=InnoDB;
INSERT INTO `user` VALUES (42, 'demo@example.test', '访客');

SELECT nickname FROM `user` WHERE id = 42;
SELECT id, email FROM `user` WHERE email = 'demo@example.test';
SELECT nickname FROM `user` WHERE email = 'demo@example.test';
```

第一句用主键在聚簇索引里直接取 `nickname`。第二句若走 `idx_email`，叶条目已经有 `email` 和主键 `id`，这条查询被索引覆盖。第三句若也走这个索引，只能先找到 `id=42`，再去主键树拿 `nickname`，这就是回表。匹配一条只多走一趟；匹配许多条时，回表可能散落到许多不同的数据页。只有一两行的实验表上优化器未必选演示中的访问路径，验证要补代表性数据并看 `EXPLAIN`。覆盖描述的是查询所需列；某些 MVCC 可见性检查仍可能访问聚簇记录，不要承诺物理上一次都不访问。

### 为什么不把所有字段都放进索引
如果热点查询只需上述三列，可以评估 `(email, nickname)`，主键仍随二级索引记录保留；但索引变宽会占更多缓存和磁盘，修改包含的列也要维护索引。先减少 `SELECT *`，再给高频且收益明确的查询做覆盖。整张表的数据都要读时，即使有索引，逐条回表也可能比扫表更贵。

### 面试怎么说
先画两棵树的叶子，再顺着“按 email 找到 id → 按 id 拿昵称”走一遍，最后补一句：覆盖是某条查询和某个索引的关系，不是另一种独立的索引类型。""",
            followups=[
                dict(q="不声明主键，是否就没有聚簇索引了？", a="不是。InnoDB 会选第一个所有键列都为 NOT NULL 的唯一索引；没有合适的唯一索引才生成隐藏行 ID，建立内部聚簇索引。"),
                dict(q="二级索引每找到一条记录就要回表吗？", a="不是。查询被覆盖时通常不必为取缺失列回表；未覆盖时也可能先用索引条件下推排掉不符合条件的记录，再为剩下的记录取整行。"),
            ],
            pitfalls=["以为二级索引叶子存的是整行或行的物理地址。", "只看 WHERE 列是否在索引上，不看 SELECT 需要取什么。"],
            hook="用不同投影对同一张表做 A/B：查询同一批 email，分别返回 id 和 nickname。记录执行计划、扫描行数、延迟和缓存状态；若计划走了全表，扩大数据量并让被筛出的记录比例更接近生产。",
            mnemonic="二级给编号，聚簇给整行；目录已够用，就不用回表取列。",
        ),
        dict(
            id="mysql-leftmost-prefix",
            q="联合索引 (a,b,c) 的最左前缀是什么意思？范围查询后面的列还能用吗？",
            level=1,
            short="联合索引按 `(a,b,c)` 的字典序排，先按 a，再在相同 a 中按 b，最后按 c。`a=1 AND b=2` 能用连续前缀定位，`a=1 AND c=3` 通常只能用 a 定位；`a=1 AND b>2 AND c=3` 通常以 a、b 定出范围，c 仍能过滤或用于覆盖。看的是索引列顺序，不是 WHERE 文本的书写顺序。",
            points=[
                "用字典序解释 (a,b,c) 为何能定位 a、(a,b)、(a,b,c)",
                "缺 a 通常无法走常规连续前缀定位；缺 b 时 c 通常不能参与定位",
                "遇到不等范围后，后续列仍能用于 ICP 过滤或覆盖，不等于完全没用",
                "条件书写顺序不改变索引的物理顺序；用计划验证是否实际选用",
            ],
            explain="""### 把索引看成按三列排序的名单
例如依次排出 `(1,1,9)、(1,2,3)、(1,2,8)、(2,1,3)`。找 `a=1` 能圈出前三条；找 `a=1,b=2` 可以缩到中间两条。只找 `b=1` 则命中第一和最后一条，中间不是一段连续区间。最左前缀讲的是能不能直接画出扫描边界，不是 SQL 能不能返回正确结果，也不是优化器一定会选它。

### 用 SQL 区分定位和过滤
```sql
CREATE TABLE prefix_demo (
    id BIGINT PRIMARY KEY, a INT NOT NULL, b INT NOT NULL,
    c INT NOT NULL, payload VARCHAR(80), KEY idx_abc (a, b, c)
) ENGINE=InnoDB;
INSERT INTO prefix_demo VALUES
    (1, 1, 1, 9, 'p1'), (2, 1, 2, 3, 'p2'),
    (3, 1, 2, 8, 'p3'), (4, 2, 1, 3, 'p4');
EXPLAIN SELECT payload FROM prefix_demo WHERE a = 1;
EXPLAIN SELECT payload FROM prefix_demo WHERE c = 3 AND b = 2 AND a = 1;
EXPLAIN SELECT payload FROM prefix_demo WHERE a = 1 AND c = 3;
EXPLAIN SELECT payload FROM prefix_demo WHERE a = 1 AND b > 1 AND c = 3;
EXPLAIN SELECT payload FROM prefix_demo WHERE b = 1;
```

第二句虽然 `a` 写在最后，却能用上三个键列作等值定位；去掉 `c` 也能用 `(a,b)`。第三句跳过 `b`，通常只定位到 `a=1` 那一段。第四句在 `a=1` 下扫 `b>1`，每个不同的 `b` 值下 `c` 都重新排序，不能当成全段都按 `c` 排。若选二级索引且满足索引条件下推（ICP）的条件，可以先在索引条目上筛 `c`，少取整行；若投影被覆盖，`c` 也可以直接从索引取。第五句通常不能靠这个连续前缀查找，仍可能扫描索引；MySQL 8.0 在满足限制且成本合适时还有 Skip Scan，因此别说成“必全表”。

### 面试怎么说
先指出是“定位范围”和“读取记录后的过滤”两件事，再说等值前缀、范围和后续列。不用背“范围后彻底失效”；要解释查询为什么还能少回表，并拿 `EXPLAIN` 的 `key`、`key_len`、`Extra` 或 JSON 版辅助判断，别用几条测试数据断言实际访问方式。""",
            followups=[
                dict(q="`b IN (2,3)` 和 `b>2` 都算范围，为何可能不一样？", a="IN 常能拆成几个等值分支。在 a 固定时，优化器可以分别构造 b=2、b=3 的键区间，再在各区间内考虑 c；连续不等范围则通常不能这样逐值展开。"),
                dict(q="有了 (a,b,c)，还要单建 (a) 吗？", a="通常先避免重复建设，因为它已经支持按 a 定位；但更窄索引可能在只扫 a 的高频场景节省页读，要按代表性负载验证收益是否值得额外维护。"),
            ],
            pitfalls=["认为把 WHERE 中的 a 写到最前面才能让索引生效。", "看到范围后的列不能继续定扫描边界，就断言该列不能参与任何索引优化。"],
            hook="用 Python 参数化这五种查询分别造高低选择性的组合，核对返回集与执行计划。再用非覆盖列触发可能的回表，对比实际扫过的记录和耗时，区分“定位更窄”与“过滤更早”。",
            mnemonic="顺序看键不看写法；先定位，后过滤。",
        ),
        dict(
            id="mysql-index-misses",
            q="哪些写法会让索引失效，建了索引为什么还会全表扫描？",
            level=1,
            short="先分两种：条件无法方便地映射成索引区间，或区间能算出来但优化器估计扫描更便宜。常见于索引列套函数、字符串列和数字比较、LIKE 左模糊、OR 一边无合适索引、联合索引缺左前缀；命中比例高又要大量回表时也可能主动扫表。用 EXPLAIN 和实际负载确认，不把现象当铁律。",
            points=[
                "索引列函数和某些隐式类型转换会妨碍按原键定位，给出等价改写",
                "区分 LIKE 'abc%' 与 LIKE '%abc'，解释左模糊破坏连续前缀",
                "OR 并非必失效；分支有合适索引时可能走同索引范围或 Index Merge",
                "联合索引缺最左前缀通常不能常规定位；全表扫描也可能是成本选择",
            ],
            explain="""### “失效”是在说哪一步
有索引不等于用索引缩小访问范围。比如 `type=index` 也可能是在扫整棵索引；如果要取的大部分行还得从二级索引回表，成本模型可能算出扫描表更便宜。排查先问两个问题：能否把条件变成键的区间？能的话，扫描区间加回表是否划算？

### 用一张表看常见反例
```sql
CREATE TABLE index_demo (
    id BIGINT PRIMARY KEY, code VARCHAR(20) NOT NULL,
    created_at DATETIME NOT NULL, note VARCHAR(100),
    KEY idx_code (code), KEY idx_created (created_at),
    KEY idx_code_created (code, created_at)
) ENGINE=InnoDB;
EXPLAIN SELECT note FROM index_demo WHERE DATE(created_at) = '2026-01-10';
EXPLAIN SELECT note FROM index_demo
WHERE created_at >= '2026-01-10 00:00:00'
  AND created_at <  '2026-01-11 00:00:00';
EXPLAIN SELECT note FROM index_demo WHERE code = 123;
EXPLAIN SELECT note FROM index_demo WHERE code = '123';
EXPLAIN SELECT note FROM index_demo WHERE code LIKE '%123';
EXPLAIN SELECT note FROM index_demo WHERE code = '123' OR note = '待核对';
```

`DATE(created_at)` 是在原键上做运算；对这个 `DATETIME` 列，按日写成左闭右开区间可以定位，也不会漏掉日末可能存在的小数秒。`VARCHAR` 与数字比较时有数值转换，`'123'` 和 `'00123'` 都可能匹配数字 123，无法用字符串键直接做同样的等值查找；如果产品本来要按文本编码匹配，应用绑定字符串参数，注意这不是保留原 SQL 的数值语义。左模糊没有固定前缀，右模糊 `LIKE '123%'` 则有。OR 中 `note` 没索引，不能只扫 `code` 的分支就获得完整结果；两边都有索引时则可能有更好的计划。只按 `created_at` 查通常不能通过 `(code, created_at)` 做常规最左前缀定位，本例另有 `idx_created` 可选。

### 面试怎么说
先用函数包列讲清“不能定位”，再用比例很高的 `SELECT note` 范围讲清“能定位但成本不划算”。遇到生产 SQL，核对列和绑定参数类型、查询列、数据分布、统计信息及计划。改写前先验证结果语义；为了消掉 OR 改成 `UNION ALL`，要小心两边都匹配的行被重复返回。""",
            followups=[
                dict(q="非得按函数结果查怎么办？", a="先业务等价地改写区间；确实要按表达式匹配时可评估生成列加索引，或在 MySQL 8.0.13 及以后评估支持的函数索引，并验证查询表达式和写入代价。"),
                dict(q="为什么测试库走索引、生产反而全表扫？", a="两边数据分布、行宽和统计信息可能不同。用生产形态的参数和值分布比较估计和实际行数，别仅用小表结论，也不应把强制索引当作首选。"),
            ],
            pitfalls=["把所有 OR、所有类型转换都说成必然全表扫描。", "只优化计划不核对结果，导致改写后前导零编码的匹配语义改变。"],
            hook="回归时专门造前导零、跨日边界和 OR 两边都匹配的数据，先断言结果，再看计划。对 ORM 或驱动记录参数实际类型，避免 SQL 文本看起来相同，线上却把字符串编码绑成数字。",
            mnemonic="先看圈不圈得到，再看圈出来值不值。",
        ),
        dict(
            id="mysql-slow-query",
            q="线上接口突然变慢，你怎么定位并优化 MySQL 慢查询？",
            level=1,
            short="先用接口耗时拆分和数据库指标确认慢在哪，再在合适窗口开启 `slow_query_log`、设 `long_query_time`，用 `mysqldumpslow` 或 `pt-query-digest` 聚合同类 SQL，按总耗时、次数和尾延迟排优先级。拿实际参数跑 EXPLAIN，区分扫描、回表、排序和锁等待；改 SQL 或索引后在同数据量同并发下复测，也看写入代价。",
            points=[
                "知道 slow_query_log 和 long_query_time；区分全局设置和会话阈值",
                "用 mysqldumpslow 或 pt-query-digest 按指纹聚合，优先排查高总耗时或高频 SQL",
                "拿代表性参数用 EXPLAIN 查扫描、回表、排序，另检查锁等待",
                "能说出组合索引、条件改写、减少回表、分批拆分和缓存各自适用条件",
                "优化后在同数据规模和并发下核对结果、延迟、扫描量及写入影响",
            ],
            explain="""### 第一步：先确定慢在哪里
某电商的订单列表变慢。先从接口监控确认时间花在数据库调用，而不是连接池排队或应用处理。经授权在低风险窗口采样慢日志，检查输出位置；下例假定测试实例已配置为写文件。降低阈值会增加日志量，先记原值，采样结束恢复；已有连接池连接不会自动继承新设的全局 `long_query_time`。

```sql
SELECT @@GLOBAL.slow_query_log, @@GLOBAL.long_query_time,
       @@GLOBAL.log_output, @@GLOBAL.slow_query_log_file;
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 0.2;
SET SESSION long_query_time = 0.2;
```

```bash
mysqldumpslow -s t -t 10 /path/to/mysql-slow.log
pt-query-digest /path/to/mysql-slow.log
```

同一模板的不同参数会被归到一起。先看总耗时和次数，再看单次耗时、扫描行数和业务影响；“一条很慢”和“每秒执行很多次导致累计很慢”都值得关注。慢日志不等于端到端计时，初始锁获取时间不计入执行时间，怀疑锁时另外看 `performance_schema.data_lock_waits` 和长事务。在隔离测试库练习时，可将测试连接的 `long_query_time` 设为 0 采样，避免下例在机器上跑得太快而进不了慢日志；不要把这个阈值用作生产的全局配置。

### 第二步：用一个可复现的列表查询找原因
列表实际只需 ID 和创建时间。下面造五万行，演示从按函数查到按原列做范围查；查询的日期比较对象是 `DATETIME`，改写前后选的是同一天。

```sql
CREATE TABLE slow_orders (
    id BIGINT PRIMARY KEY, tenant_id INT NOT NULL, status TINYINT NOT NULL,
    created_at DATETIME NOT NULL, detail VARCHAR(200) NOT NULL
) ENGINE=InnoDB;
INSERT INTO slow_orders (id, tenant_id, status, created_at, detail)
WITH RECURSIVE seq(n) AS (
    SELECT 0 UNION ALL SELECT n + 1 FROM seq WHERE n < 999
)
SELECT num + 1, MOD(num, 100), MOD(num DIV 100, 4),
       TIMESTAMPADD(MINUTE, num, '2026-01-01 00:00:00'), REPEAT('x', 120)
FROM (SELECT aa.n + 1000 * bb.n AS num FROM seq AS aa
      CROSS JOIN seq AS bb WHERE bb.n < 50) AS nums;

EXPLAIN SELECT id, created_at FROM slow_orders
WHERE tenant_id = 7 AND status = 1 AND DATE(created_at) = '2026-01-10'
ORDER BY created_at DESC, id DESC LIMIT 20;

ALTER TABLE slow_orders ADD INDEX idx_list (tenant_id, status, created_at, id);
EXPLAIN SELECT id, created_at FROM slow_orders
WHERE tenant_id = 7 AND status = 1
  AND created_at >= '2026-01-10 00:00:00' AND created_at < '2026-01-11 00:00:00'
ORDER BY created_at DESC, id DESC LIMIT 20;
```

优化前没有适合的二级索引，需要大量扫描并排序。优化后目标是用等值前缀定位租户和状态，再取时间区间，用索引逆序读满足列表顺序，同时覆盖投影。对照计划检查 `key`、`rows`、`Extra`，不要编一个固定的提速倍数。要区分改写和建索引各自的贡献，可在两版 SQL 上分别加索引前后跑四组对照。

### 第三步：复测、上线和取舍
在测试环境用冷热参数测结果集、P95、扫描量和写入吞吐；MySQL 8.0.18 起可用 `EXPLAIN ANALYZE` 看实际执行，但它真跑查询。若是大批量操作拖长事务，可按主键拆小批并设计断点；若是高频、可容忍短暂过期的读，可再评估缓存、失效与回源，不能拿缓存遮住锁争用。上线还要评估 DDL、空间和新增索引维护成本，灰度观察并准备回退。

### 面试怎么说
按“确认是数据库 → 聚合日志定优先级 → 计划和证据定原因 → 改写加索引 → 同负载复测”讲一遍，比只回答“开日志、加索引”完整。""",
            followups=[
                dict(q="慢日志只记录单次慢 SQL，怎样找高频的开销？", a="按指纹看总耗时和次数；低于慢日志阈值的高频语句可能漏采，可结合性能库的语句摘要或短窗口降低阈值采样，并留意采样开销。"),
                dict(q="计划看着没问题，为什么高峰期才慢？", a="可能是锁、连接池或 I/O 排队，而不是访问路径。要拿高峰期的等待事件、阻塞事务和实际绑定值对时间，不能只在无并发的空闲库测一次。"),
            ],
            pitfalls=["只看最慢的一条，忽略总耗时更高的一组。", "在生产长期把阈值调得很低，或直接执行未经评估的 EXPLAIN ANALYZE。"],
            hook="把原 SQL 和改写版接入压测回归：固定数据快照和并发，断言 ID 顺序一致，采集 P95、扫描行数、锁等待和写入吞吐。上线后用同一 SQL 指纹对比高峰窗口，避免把流量变化误作优化收益。",
            mnemonic="采日志、聚指纹、看计划、找等待、做对照。",
        ),
        dict(
            id="mysql-explain",
            q="一条 SQL 的 EXPLAIN 输出，你会先看哪些字段？",
            level=1,
            short="先用 `type` 判断各表怎么读：ALL 是全表扫，index 是全索引扫，range 是区间，ref 是按键找多条候选，eq_ref 是每个外层组合最多匹配一条，const 是常量键最多一条。再看 `key` 用了什么索引、`rows` 估计读多少、`filtered` 估计过滤后剩多少百分比，最后看 Extra 有没有覆盖、排序或临时表。",
            points=[
                "正确区分 ALL、index、range、ref、eq_ref、const 的访问方式",
                "key 是实际选用的索引，possible_keys 是候选；key_len 可辅助判断键前缀",
                "rows 和 filtered 都是估计值，rows × filtered / 100 约等于本步留下的行数",
                "读懂 Using index、Using where、Using filesort、Using temporary，不将它们等同于好坏",
                "能区分普通 EXPLAIN 与会实际执行查询的 EXPLAIN ANALYZE",
            ],
            explain="""### 先看优化器打算怎么取行
`EXPLAIN` 像施工方案，不是耗时报告。以传统表格输出为例，通常按每张表看访问路径，下游表还可能被上游结果驱动多次。

| type | 直觉 | 典型情况 |
|---|---|---|
| ALL | 全表扫描 | 没有划算的索引路径 |
| index | 全索引扫描 | 按索引顺序读，可能比扫整行窄，但不是点查 |
| range | 扫一个或多个键区间 | 主键 BETWEEN 一段区间 |
| ref | 用键的等值值找可能的多行 | 按非唯一索引查同一用户的订单 |
| eq_ref | 对前面表的每个行组合最多匹配一行 | JOIN 的内表按完整主键或非空唯一键匹配 |
| const | 以常量定位至多一行，表只读一次 | WHERE 主键 = 常量 |

接着看 `key`，不要把 `possible_keys` 的候选当成已选。`rows` 是估计检查的行数，`filtered` 是估计通过该表条件的百分比；同一步 `rows=1000, filtered=10.00` 约留 100 行。如果这一步被多次驱动，总工作量还要考虑上游次数；不能把每行的 `rows` 直接相加当总扫描量。

### Extra 为什么值得看
`Using index` 通常表示索引覆盖，和访问方式 `type=index` 不是同一回事；`Using where` 表示还要按条件筛行，不等于没用索引；`Using filesort` 表示有额外排序步骤，可能在内存完成，不一定写磁盘；`Using temporary` 表示用了内部临时表，也不一定落盘。它们是排查线索，不是“出现就必须消掉”的评分项。几十条候选做排序，可能比为了消除排序新建一个宽索引更划算。

### 拿两张表按顺序读
```sql
CREATE TABLE plan_user (id BIGINT PRIMARY KEY, nickname VARCHAR(40)) ENGINE=InnoDB;
CREATE TABLE plan_order (
    id BIGINT PRIMARY KEY, user_id BIGINT NOT NULL, amount DECIMAL(10,2),
    KEY idx_user (user_id)
) ENGINE=InnoDB;
INSERT INTO plan_user VALUES (1, '访客'), (2, '新用户');
INSERT INTO plan_order VALUES (10, 1, 19.00), (11, 1, 25.00), (12, 2, 5.00);
EXPLAIN SELECT id FROM plan_order WHERE user_id = 1;
EXPLAIN SELECT oo.id, uu.nickname
FROM plan_order AS oo JOIN plan_user AS uu ON uu.id = oo.user_id
WHERE oo.id BETWEEN 10 AND 20 ORDER BY oo.amount DESC;
```

第一条若用 `idx_user`，典型是 `ref` 且覆盖 `id`；第二条可从订单主键扫范围，再用用户主键匹配，按金额可能另做排序。小样本无需强求实际计划长成这样；上线判断要结合真实分布。估算与实测差距大，先检查统计信息与参数偏斜。

### 面试怎么说
按“访问方式 → 选了谁 → 扫多少留多少 → 还有什么额外工作”读一遍。最后强调估计不等于实测，8.0.18 起可在安全环境用 `EXPLAIN ANALYZE` 校验实际行数和循环数。""",
            followups=[
                dict(q="`type=index` 是不是一定比 `ALL` 快？", a="不一定。前者仍可能扫大量索引页，还可能有额外取行成本；看实际读取行数、投影是否覆盖、缓存和耗时，而不是只拿访问类型排序。"),
                dict(q="预估一百行，实测十万行，接下来查什么？", a="先用同一组绑定参数与数据分布复现，再检查统计信息是否过时或值分布偏斜；连接还要确认放大出在哪一层，不要只比较最终返回行数。"),
            ],
            pitfalls=["把 rows 当作准确返回行数，或忘了连接内表可能循环多次。", "看到 filesort 就认定写了磁盘，或把 Using index 和 type=index 混为一谈。"],
            hook="给查询回归加高、低选择性两组参数，记录估算行数和实际行数、循环数。计划可能随版本和统计信息变化，比起把某个 type 写成死断言，更适合设业务延迟和扫描量上限，再留计划用于定位。",
            mnemonic="先看怎么读，再看读多少，最后看额外做什么。",
        ),
        dict(
            id="mysql-acid",
            q="事务的 ACID 分别是什么？InnoDB 靠什么做到？",
            level=1,
            short="拿转账说：原子性是扣款和入账要么都生效、要么都撤销，回滚靠 undo log；持久性是已提交结果在相应刷盘保障下能抗崩溃，靠 redo log 恢复；隔离性靠锁和 MVCC，效果取决于隔离级别；一致性是最终目标，要让数据库约束和业务不变量在事务前后都成立，不是某一种日志直接提供的。",
            points=[
                "原子性是全做或全不做，undo log 提供回滚所需的旧信息",
                "持久性靠预写 redo 和恢复，承诺还受刷盘配置与存储保障影响",
                "隔离性靠锁协调并发写和加锁读，靠 MVCC 做快照读，强度取决于级别",
                "一致性是目的，数据库约束加业务规则共同守住不变量",
            ],
            explain="""### 为什么不能让每句 SQL 都单独提交
转账不是两条彼此无关的更新。如果扣完钱就提交，进程在入账前崩溃，总余额就凭空少了一块。事务把两次修改绑成一个提交单元，但“写进同一事务”仍不能替代余额校验和幂等逻辑。

### 用一笔 30 元的转账拆 ACID
```sql
CREATE TABLE acid_account (id BIGINT PRIMARY KEY, balance INT NOT NULL) ENGINE=InnoDB;
INSERT INTO acid_account VALUES (1, 100), (2, 50);
START TRANSACTION;
UPDATE acid_account SET balance = balance - 30 WHERE id = 1 AND balance >= 30;
SELECT ROW_COUNT() AS debited;
UPDATE acid_account SET balance = balance + 30 WHERE id = 2;
SELECT ROW_COUNT() AS credited;
COMMIT;
SELECT id, balance FROM acid_account ORDER BY id;
```

这组固定数据上，两次影响行数都为 1，结果是 70 和 80，总和仍是 150。真实应用在扣款为 0 时不应继续入账，入账更新如果没有命中也要 `ROLLBACK`；加上错误处理，不能照着样例走无条件提交。想验证原子性，可以重新初始化后在第一次更新完成立即回滚，而非顺着示例再执行后续语句。

| 性质 | 说人话 | 机制与边界 |
|---|---|---|
| A 原子性 | 要么都做，要么都不做 | undo 留下撤销信息；事务回滚能撤掉已做的修改。 |
| C 一致性 | 从一个合法状态到另一个合法状态 | 唯一键、外键等管可表达的规则；总额守恒、金额为正等仍要由业务正确维护。 |
| I 隔离性 | 并发时彼此影响要有规则 | 写入用锁协调；普通快照读用 MVCC 找可见版本，不同级别的可见结果有差异。 |
| D 持久性 | 已提交不等于只改了内存 | 页可稍后落盘；按预写日志和相应刷盘保障，用 redo 恢复尚未落到数据页的更新。 |

### 不要用数据库承诺本来不承诺的事
把同一个金额错写进两边，就算事务原子提交也可能破坏业务含义；如果重试没有去重，同笔订单还可能扣两次。若动作还包含另一个系统的调用，本地 rollback 也不能撤销外部副作用。持久性同样有前提：放宽日志刷盘会换吞吐但增加崩溃丢失窗口，单机日志也不是存储介质损坏后的备份。

### 面试怎么说
用一笔转账把四个词连起来，最后说“事务给我手段，守恒和幂等仍要由业务设计”，不要把 C 背成某个参数。""",
            followups=[
                dict(q="应用收到提交超时，能直接重试转账吗？", a="不能把超时当作没提交。应带同一个业务幂等键重试或查询终态，用唯一约束及事务避免重复记账，并明确返回已完成和待确认的区别。"),
                dict(q="一句 UPDATE 失败，前面已成功的 UPDATE 会自动撤销吗？", a="不保证。错误类型影响回滚范围，有些只回滚当前语句；应用应显式处理事务失败并回滚，而不是捕获异常后继续提交前几条修改。"),
            ],
            pitfalls=["把一致性说成由 redo 或 undo 单独实现。", "把语句报错当成所有场景都自动回滚整笔事务。"],
            hook="给转账链路注入三种故障：扣款后异常、入账目标不存在、提交响应超时。同一请求 ID 重试后断言两边总额守恒、余额不为负、流水只有一条；另开连接观察可见状态，别用原事务自己的读结果冒充已提交。",
            mnemonic="A 能撤，D 能恢复，I 管并发，C 守规则。",
        ),
        dict(
            id="mysql-isolation-levels",
            q="四种事务隔离级别怎么区分？脏读、不可重复读、幻读分别是什么？",
            level=1,
            short="脏读是读到别人未提交的值；不可重复读是同一行前后读到不同的已提交版本；幻读是同一范围前后返回的行集合变了。隔离从 RU、RC、RR 到 Serializable 逐步加强，InnoDB 默认 RR。别把标准表直接当成实现，InnoDB 的 RR 普通快照读和加锁范围读分别用 MVCC 和范围锁处理幻读。",
            points=[
                "区别未提交值、同一行版本变化、同一谓词命中集合变化三种异常",
                "说出 RU、RC、RR、Serializable 的顺序及标准对三现象的最低要求",
                "指出 InnoDB 默认 RR，且其快照读表现比标准最低要求更强",
                "说明隔离越强并发越可能受限制，应用要按读写语义选择",
            ],
            explain="""### 两台客户端看到的不是同一时刻
下面每行都是一次独立实验：先重置样本，A 整段为同一事务，B 负责修改。这里的读是普通 `SELECT`，不是加锁读。不可重复读和幻读容易混：前者盯一条已存在的记录看值，后者盯一个谓词看符合条件的记录集合。

| 现象 | 第一步 | 第二步 | 第三步 |
|---|---|---|---|
| 脏读 | B 把 id=1 的 100 改为 90，不提交 | A 读到 90 | B 回滚，90 从未成为提交结果 |
| 不可重复读 | A 读 id=1 得 100 | B 改为 90 并提交 | A 再读 id=1 得 90 |
| 幻读 | A 数 id 在 1 至 5 的行，得 2 | B 插入 id=3 并提交 | A 按同一条件计数，得 3 |

### 四级的标准对照与实际表现
“可能”指该隔离级别最低要求没有禁止，不是每次都复现。

| 隔离级别 | 脏读 | 不可重复读 | 幻读 |
|---|---|---|---|
| READ UNCOMMITTED（RU） | 可能 | 可能 | 可能 |
| READ COMMITTED（RC） | 禁止 | 可能 | 可能 |
| REPEATABLE READ（RR） | 禁止 | 禁止 | 标准允许出现 |
| SERIALIZABLE | 禁止 | 禁止 | 禁止 |

InnoDB 默认 RR，同一事务的普通一致性读通常复用首次这类读建立的快照，不会凭空看到别人后来插入的行；在 RR 下要锁住一个搜索范围时，则看加锁读及其访问路径。Serializable 更强调把结果约束为可串行执行的效果；例如在关闭 autocommit 的事务中，InnoDB 会把普通 SELECT 隐式当成 `SELECT ... FOR SHARE`，冲突可能等待，不等于服务器只允许一个连接。

### 双连接复现 RC 的幻读
```sql
CREATE TABLE isolation_demo (id INT PRIMARY KEY, amount INT NOT NULL) ENGINE=InnoDB;
INSERT INTO isolation_demo VALUES (1, 100), (5, 50);

-- A：执行到第一次 SELECT，暂停
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;
SELECT COUNT(*) FROM isolation_demo WHERE id BETWEEN 1 AND 5;

-- B：另一连接执行完成再切回 A
START TRANSACTION;
INSERT INTO isolation_demo VALUES (3, 80);
COMMIT;

-- A：继续，计数从 2 变 3
SELECT COUNT(*) FROM isolation_demo WHERE id BETWEEN 1 AND 5;
COMMIT;
```

重新清理 `id=3` 后将 A 换成 `REPEATABLE READ` 再跑，正常快照读下第二次仍是 2。A 提交再读才会看到 B 的已提交结果。要比较读到 100 还是 90，则用同一主键做两次普通 SELECT，切换中间的 B 操作即可。

### 面试怎么说
先把三种现象说准，再讲“两张表”：标准允许什么、InnoDB 实际怎么做；不要只背一个 RR 必有或绝无幻读的结论。""",
            followups=[
                dict(q="RC 为什么还可以发生不可重复读？", a="RC 每次普通一致性读用新的快照，只保证这次读不拿别人的未提交版本。B 在 A 两次读取之间提交同一行的新值，第二次就可能读到它。"),
                dict(q="隔离级别越高越好吗？", a="要先问业务是不是需要同一快照或锁住范围。更强的隔离可能增加锁竞争和重试；防重复下单常该先用唯一键，不是先把所有事务切到 Serializable。"),
            ],
            pitfalls=["把看到别人已经提交的新值叫脏读。", "把 SQL 标准允许幻读说成 InnoDB 的 RR 普通快照读必然会出现幻读。"],
            hook="用两条独立数据库连接和线程屏障控制读、提交、再读的顺序，不要靠 sleep 赌执行时机。分别断言是否阻塞、返回值及行集合；每个用例后清理数据并恢复连接池的会话隔离级别。",
            mnemonic="脏看未提交，重读看同一行，幻看一组行。",
        ),
        dict(
            id="mysql-mvcc",
            q="InnoDB 的 MVCC 怎么找可见版本？RC 和 RR 有什么区别？",
            level=2,
            short="普通 SELECT 可以读快照，不必为了别的事务正在修改同一行而等它提交。聚簇记录上的 `DB_TRX_ID` 标记最近修改的事务，`DB_ROLL_PTR` 指向 undo，可沿版本链找旧值；Read View 决定哪个版本可见。RC 每次一致性读建新视图，RR 默认复用第一次一致性读的视图。加锁读和修改则面向当前记录，要处理锁冲突。",
            points=[
                "说出 DB_TRX_ID、DB_ROLL_PTR 的角色和 undo 版本链",
                "Read View 记录创建时的活跃事务及边界，不可见则沿 undo 找更旧版本",
                "读得到自己写的修改，Read View 不是数据库整表的物理副本",
                "RC 每次一致性读新建视图，RR 默认由首次一致性读建立并复用",
                "普通快照读与 SELECT FOR UPDATE、UPDATE 等当前访问语义不同",
            ],
            explain="""### 为什么不干脆让读等写
假设一笔扣款还没提交，报表只是想看一个一致的已提交视图，不必排队等它。多版本并发控制（MVCC）保存重建历史记录所需的信息，读者可以沿版本链拿自己看得到的那版；这不代表写写冲突也能不加锁。

### 版本链和 Read View 怎么配合
聚簇记录上的 `DB_TRX_ID`（`trx_id`）标记最近一次插入或修改它的事务，`DB_ROLL_PTR`（`roll_pointer`）指向 undo 记录，用来重建修改前的记录。连续修改形成一条能往回追的链。Read View 记下创建时活跃的读写事务 ID 及可见性判断的边界，不是把整表复制一份。简化理解：自己的修改可见；在视图建立时还活跃或随后才开始的其他修改不可见；已在视图建立前提交的版本通常可见。最新版本不符合就沿 undo 向前找；如果这行当时还没出现，就读不到它。

例如版本链是 `80（后来事务写入）→ 90（视图前已提交）→ 100（更旧）`，A 的视图判定 80 不可见，回到 90 即停，不是总读最旧的那版。很老的活跃快照会让清理线程暂时不能删掉它仍有可能用到的 undo。

### 一张表区分 RC、RR 和当前读
```sql
CREATE TABLE mvcc_demo (id INT PRIMARY KEY, amount INT NOT NULL) ENGINE=InnoDB;
INSERT INTO mvcc_demo VALUES (1, 100);

-- A：开启事务并读第一次，然后暂停
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
START TRANSACTION;
SELECT amount FROM mvcc_demo WHERE id = 1;

-- B：另一连接修改并提交
START TRANSACTION;
UPDATE mvcc_demo SET amount = 90 WHERE id = 1;
COMMIT;

-- A：两种读法分别得到 100 和 90
SELECT amount FROM mvcc_demo WHERE id = 1;
SELECT amount FROM mvcc_demo WHERE id = 1 FOR UPDATE;
COMMIT;
```

若重置数据并把 A 换成 RC，第二次普通读就看得到 90，因为每次普通一致性读都建新视图。RR 的 `START TRANSACTION` 本身通常还没建立快照；若 B 在 A 第一次普通读之前已经提交，A 第一次就可能读到 90。`FOR UPDATE` 面向要锁定的当前数据，不复用那个旧快照；如果 B 还没提交且持有冲突锁，就可能先等。更新和删除同样不能只拿报表看到的历史值去修改。

### 面试怎么说
分三句：“undo 让我找得到旧版本，Read View 告诉我能看哪版，隔离级别决定何时换视图。”再补：“查完马上要改，别把快照查到的值直接当成加锁后的值。”""",
            followups=[
                dict(q="RR 想在事务开始时就取快照，怎么做？", a="在 RR 下可以用 START TRANSACTION WITH CONSISTENT SNAPSHOT 主动建立一致性快照；普通 START TRANSACTION 默认等首次一致性读，不要把两者等同。"),
                dict(q="为什么长时间只读的事务也可能造成问题？", a="如果它持有老快照，清理线程不能删仍可能被它读取的历史版本，undo 历史可能变长；监控长事务及历史链变化，确认读完确实结束事务。"),
            ],
            pitfalls=["说 RR 一调用 START TRANSACTION 就一定建立 Read View。", "以为 Read View 是物理备份，或以为 MVCC 用 redo 重建旧版本。"],
            hook="在自动化用例里对调“B 提交”和“A 首次 SELECT”，区分 RR 的事务开始与快照建立。再增加 A 改写后的自读、B 未提交时的 FOR UPDATE 等待，避免只写两次快照读的顺利路径。",
            mnemonic="undo 找历史，视图挑版本；RC 每次换，RR 首读定。",
        ),
        dict(
            id="mysql-lock-types",
            q="InnoDB 的共享锁、意向锁、记录锁和间隙锁怎么区分？",
            level=1,
            short="共享锁 S 之间兼容，排他锁 X 与同资源的其他 S、X 冲突。InnoDB 有表锁和基于索引的行锁；表级 IS、IX 向整表锁声明下面要拿 S 或 X。记录锁保护索引记录，间隙锁防在键间空隙插入，临键锁是记录加它前面的间隙。访问路径不够窄时可能锁住很多索引记录，而不是自动升级成一把表 X 锁。",
            points=[
                "说出共享 S、排他 X 的冲突关系，以及表与索引记录的锁粒度",
                "意向锁 IS、IX 在表级声明下层加锁意图，服务于整表与行的协调",
                "区别记录锁、间隙锁、临键锁；临键锁是记录加其前间隙",
                "行锁锁索引记录；没有合适索引可能扫描和锁住很多记录",
                "说明完整唯一键命中和范围扫描的锁覆盖通常不同",
            ],
            explain="""### 先分锁什么，再分允许谁一起用
S（共享）像允许多人看同一份材料，X（排他）像一个人拿着材料修改；对同一条记录，不同事务的 S 可共存，X 与别人的 S 或 X 冲突。`SELECT ... FOR SHARE` 可以显式加共享锁，`SELECT ... FOR UPDATE` 会为要检查锁定的记录取得排他性质的锁；普通一致性读不因此自动等行锁。表级意向锁 IS / IX 提示“我在这张表下面持有或准备持有行 S / X”，让整表锁请求知道下层有人使用，不用挨行找。两个事务拿 IX 不意味着它们必冲突，仍要看是否碰到同一批记录。表级意向锁也不是防 DDL 的元数据锁。

### 锁住的是索引记录和相邻间隙
假设有主键 10、20、40。记录锁针对已有键，比如 20；间隙锁针对空隙，比如 `(10,20)`，目的是阻止在这里插入，不等于把 20 这条记录锁死；临键锁（next-key lock）可以表示成 `(10,20]`，同时保护间隙和右端记录。在默认 RR 下，完整唯一键等值且命中通常只需记录锁，非唯一或范围访问可能拿临键锁，实际范围取决于访问路径。二级索引的排他搜索还可能锁相应聚簇记录。

### 两条查询表面都只取一行
```sql
CREATE TABLE lock_demo (
    id INT PRIMARY KEY, tag VARCHAR(30) NOT NULL
) ENGINE=InnoDB;
INSERT INTO lock_demo VALUES (10, 'first'), (20, 'target'), (40, 'other');
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
START TRANSACTION;
SELECT * FROM lock_demo WHERE id = 20 FOR UPDATE;
ROLLBACK;
START TRANSACTION;
SELECT * FROM lock_demo WHERE tag = 'target' FOR UPDATE;
ROLLBACK;
```

主键能直接定位 20；`tag` 没索引，第二条可能扫描整个聚簇索引，在 RR 下会把锁的足迹扩大。实验时在 A 的 `ROLLBACK` 之前用 B 更新 id=40，对比两种路径下 B 是否等待。表看起来像被“锁住”不代表发生了锁升级；即使没有声明任何用户索引，InnoDB 仍有聚簇索引供记录加锁。

### 面试怎么说
不要只报锁名。先问“是普通读还是加锁读、走哪个索引、条件是唯一等值还是范围、隔离级别是什么”，再画锁覆盖的记录和间隙。""",
            followups=[
                dict(q="查一个不存在的唯一键，还能说只加记录锁吗？", a="不能，缺失键没有对应记录可锁。默认 RR 下加锁查找可能保护该键应落入的间隙，所以不能把唯一等值命中时的结论套给未命中。"),
                dict(q="RC 就完全没有间隙锁了吗？", a="一般搜索和扫描在 RC 下不使用间隙锁防幻读，但外键约束检查和重复键检查仍可能需要间隙锁；定位时要区分语句与约束触发的路径。"),
            ],
            pitfalls=["把 IX 当作锁住全表的排他锁。", "没索引就断言自动升级成表锁，忽略访问路径和隔离级别。"],
            hook="在 A 持有锁时用 B 分别修改目标行、邻近行并插入键间空隙，给每步独立清理和超时。结合执行计划和 performance_schema.data_locks 核对索引名及锁模式，别只拿响应耗时猜。",
            mnemonic="S 共享、X 排他，意向在表；记录锁点、间隙防插、临键两者合。",
        ),
        dict(
            id="mysql-phantom-locking",
            q="InnoDB 的 RR 怎么防幻读？SELECT FOR UPDATE 在这里做了什么？",
            level=2,
            short="要区分两种读。RR 的普通快照读复用 Read View，别人新插入并提交的记录不在旧视图里；加锁范围读用 next-key 等锁保护索引记录和间隙，让别的事务不能在受保护的范围插入。`SELECT ... FOR UPDATE` 读当前可锁定的数据，为后续操作持锁到事务结束，不能拿旧快照与当前读互比来证明同一种读失效。",
            points=[
                "RR 普通快照读靠同一 Read View 不看见晚提交插入",
                "RR 加锁范围读靠索引范围的 next-key 等锁限制插入",
                "SELECT FOR UPDATE 应置于显式事务内，行锁随提交或回滚释放",
                "能给出两个连接演示快照仍旧、当前范围读阻塞插入的区别",
                "区分混用快照读和当前读的结果差异与同类读的幻读",
            ],
            explain="""### 同一个“没有新行”，有两种原因
例如按 ID 读取 10 到 20，要么允许别人插入但本事务还是看旧快照，要么禁止别人在我结束之前插进保住的范围。普通 RR SELECT 是前者；在范围上做加锁读时，InnoDB 常用临键锁实现后者。只锁住 10 和 20 这两条记录不够，因为别人可以插 15，必须看记录之间的间隙。

### 双连接：只看旧快照，还是把范围锁住
```sql
CREATE TABLE phantom_demo (id INT PRIMARY KEY, amount INT NOT NULL) ENGINE=InnoDB;
INSERT INTO phantom_demo VALUES (10, 1), (20, 1), (40, 1);

-- A：读完暂停；做第二次实验时，把下面的读改成带 FOR UPDATE
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
START TRANSACTION;
SELECT id FROM phantom_demo WHERE id BETWEEN 10 AND 20;

-- B：另一连接执行；若 INSERT 正等待，切回 A，不要等 B 才继续
START TRANSACTION;
INSERT INTO phantom_demo VALUES (15, 1);
COMMIT;

-- A：再读并结束事务
SELECT id FROM phantom_demo WHERE id BETWEEN 10 AND 20;
COMMIT;
```

第一次实验 A 普通读到 10、20，B 可插入并提交，A 再普通读仍是 10、20。第二次先清理 15，A 第一条查询改为 `SELECT id FROM phantom_demo WHERE id BETWEEN 10 AND 20 FOR UPDATE;`，第二条也用相同加锁读。范围扫描保护 `(10,20)`，B 插 15 等待；A 再读后提交，B 才能继续（未超时的前提下），随后由 B 提交。实验要保持两个连接事务独立，不要一次粘完交叉步骤。通过 `data_lock_waits` 可以区分“真的等锁”与客户端没有把指令发出去。

### 混用两类读时别偷换结论
假如 A 首次普通读后，B 先提交了 15，A 这时才用 `FOR UPDATE`，它可能看到 15 并锁住相应范围；此前的快照没有拦 B 插入。若业务要“查余额然后改”，在显式事务中先对目标记录加锁或直接用带条件的原子更新；只加锁后立即提交，再用另一事务更新，不会持有原来的锁。做全局唯一性约束时先考虑唯一索引，不要仅靠手写范围锁。

### 面试怎么说
用两句话答完：“快照读是别人能插但我看不见；当前范围读是锁住间隙，别人暂时插不进。”再加限定：观察隔离级别、索引访问范围和事务边界。""",
            followups=[
                dict(q="FOR UPDATE 是不是所有 SELECT 都应该加？", a="不是，只读报表通常用普通快照读。加锁会让写入甚至其他加锁读等待；只有后续判断依赖当前数据且需要保护时，才把查和改放进尽可能短的事务。"),
                dict(q="切换到 RC 后，这个插入实验会变成什么样？", a="RC 的普通读每次取新视图，B 提交后可看到 15；范围加锁读一般只锁扫描到的记录而不靠间隙锁阻挡本例的插入，外键和重复键检查等情况另看。"),
            ],
            pitfalls=["说 MVCC 禁止了其他事务插入，实际是旧快照不可见。", "把 A 的首次快照读与后续加锁读的差异当成同类读的反例。"],
            hook="把同一 SQL 分为普通读、加锁读两组，记录 B 的插入是否先于 A 结束、A 第二次返回的 ID 和事务结束后的最终结果。每轮都清理样本并显式结束事务，防止连接池残留锁污染下一例。",
            mnemonic="快照让新行看不见，范围锁让新行暂时进不来。",
        ),
        dict(
            id="mysql-deadlock",
            q="MySQL 死锁怎么产生、怎么查、怎么避免？",
            level=2,
            short="死锁是等待形成环，比如 A 持有行 1 等行 2，B 持有行 2 等行 1。默认开启死锁检测时，InnoDB 会选一个事务整体回滚，另一个才能继续。用 `SHOW ENGINE INNODB STATUS` 的 `LATEST DETECTED DEADLOCK` 看双方 SQL、索引和锁；避免时统一加锁顺序、缩短事务、让索引减少扫描，应用对整笔事务做有限幂等重试。",
            points=[
                "给出两个事务各持一把锁、交叉等待形成环的时序",
                "默认检测等待环并选牺牲事务整体回滚，不等于普通锁等待超时",
                "能在 SHOW ENGINE INNODB STATUS 查 LATEST DETECTED DEADLOCK，分析已持有和所等的锁",
                "从加锁顺序、事务长度和索引访问范围降低死锁概率",
                "遇 1213 后在新事务做有限重试，保护重复请求的业务副作用",
            ],
            explain="""### 等待不等于死锁，环才是关键
只有 A 等 B 时，B 做完就能唤醒 A；若 B 反过来还要等 A 释放手里那把锁，双方都走不下去。以下 `UPDATE` 利用主键点查，在测试库里可以用两条连接交错执行。B 在见到 A 的第三步已发送且等待后再执行下一条。

```sql
CREATE TABLE deadlock_demo (id INT PRIMARY KEY, amount INT NOT NULL) ENGINE=InnoDB;
INSERT INTO deadlock_demo VALUES (1, 10), (2, 20);
```

| 时序 | A 连接 | B 连接 |
|---|---|---|
| 1 | `START TRANSACTION;` | `START TRANSACTION;` |
| 2 | `UPDATE deadlock_demo SET amount = amount + 1 WHERE id = 1;` | `UPDATE deadlock_demo SET amount = amount + 1 WHERE id = 2;` |
| 3 | `UPDATE deadlock_demo SET amount = amount + 1 WHERE id = 2;`（等待） | — |
| 4 | 还在等 B 释放 2 | `UPDATE deadlock_demo SET amount = amount + 1 WHERE id = 1;`（构成环） |
| 5 | 存活方完成剩余步骤并提交 | 牺牲方收到 1213，整个事务被回滚；不保证是哪一方 |

### 如何找出环上的两段边
```sql
SHOW ENGINE INNODB STATUS;
```

执行需要相应权限。在输出的 `LATEST DETECTED DEADLOCK` 找当时的事务、语句、持有和正在请求的锁，留意索引名及记录或间隙。这个区域只展示最近一次，最好及时采集，并与应用请求日志对上；复盘时还要根据事务内之前的语句找出第一把锁是谁拿的。`performance_schema.data_lock_waits` 适合看此刻正在发生的等待，不是完整历史。默认开启死锁检测，InnoDB 会尝试选回滚代价较小的事务，不保证选哪方；关闭检测时，依赖锁等待超时解除僵局。普通超时 1205 默认只回滚等待失败的语句，与 1213 的整笔回滚不同，应用不能捕获后顺手提交其余更新。

### 降低概率，也要准备善后
统一按主键顺序加锁，即使转账方向反过来也先锁较小的账户 ID；减少事务里的网络请求和大批次，给条件合适的索引减少锁足迹。复杂范围与二级索引仍可能发生死锁，别承诺彻底消除。处理 1213 时从新事务重跑完整业务步骤，限制次数并做退避；幂等键或约束兜住重复副作用，不只重发出错的那条 SQL。

### 面试怎么说
画出 `A → B → A`，说明如何从报告还原这条环，再说“固定顺序避环，有限重试兜底”，不要以提高锁等待超时来解决死锁。""",
            followups=[
                dict(q="为什么只重试收到 1213 的 UPDATE 不行？", a="牺牲事务已整体回滚，之前成功的修改以及它们的锁都没了。只重试最后一句会漏更新，要开新事务重新读取、校验并执行整个业务单元。"),
                dict(q="给表加索引就一定能避免死锁吗？", a="索引可能缩小扫描和加锁范围，减少冲突，但不同顺序仍可能形成环，写入也要维护二级索引；要结合实际死锁报告检查所有相关访问路径。"),
            ],
            pitfalls=["把任何锁等待都叫死锁，或者说等待超时就回滚整个事务。", "只复述报错 SQL，忽略同一事务内更早拿到的锁。"],
            hook="用两个连接和线程屏障分别持有第一把锁，再发交叉更新。断言一方收到 1213、牺牲方第一次修改也被撤销，存活方可继续；最后检验幂等重试不会扣账两次。",
            mnemonic="先找等待环，再固定顺序；出错重跑整笔。",
        ),
        dict(
            id="mysql-transaction-logs",
            q="redo log、undo log 和 binlog 有什么区别，为什么要两阶段提交？",
            level=2,
            short="redo 是 InnoDB 的预写日志，用来在崩溃后重放没落到数据页的修改；undo 用来回滚，也供 MVCC 找旧版本；binlog 是 Server 层的变更事件日志，用于复制和时间点恢复。启用 binlog 时，内部两阶段提交协调 InnoDB 的 redo prepare、写 binlog、redo commit。恢复时对未决事务用有效 binlog 的提交证据决策，防止两边各说各话。",
            points=[
                "redo 记录可用于重做的页修改信息，支持预写日志和崩溃恢复",
                "undo 保存撤销和构造旧版本所需的信息，支持回滚与 MVCC",
                "binlog 位于 Server 层，支持复制和配合备份做时间点恢复",
                "启用 binlog 时说明 redo prepare → 写 binlog → 引擎 commit 的顺序",
                "说出有效 binlog 内是否有提交证据，决定相应未决事务提交或回滚",
            ],
            explain="""### 三种日志回答三个不同问题
假设库存从 8 改到 7，内存页已经改好，磁盘上的数据页可能还是 8。要分别处理恢复、撤销以及把已提交的业务变化传给副本，不能靠同一种日志的名字去猜。

| 日志 | 谁负责 | 解决什么问题 |
|---|---|---|
| redo log | InnoDB | 预写修改信息，崩溃恢复时重做需要重放的页修改，不必每笔提交都刷全部数据页。 |
| undo log | InnoDB | 需要撤销时恢复旧状态；快照读也能借它构造之前的记录版本。 |
| binlog | MySQL Server | 在启用时写入变更事件；作为复制输入，也可和全量备份配合做时间点恢复。 |

binlog 可以记录行变化或语句等形式的事件，不是 InnoDB 页修改清单。redo 可在 checkpoint 推进后复用空间，也不是供副本长期追赶的历史。事务修改产生的 redo 就算被刷过，也不证明事务提交了；恢复还要处理未完成事务。

### 最怕一边成功、另一边没跟上
拿上面的扣库存来说：若本地先确认提交，再写 binlog，恰好中间断电，就可能出现本地库存为 7，而副本无事可做；若反过来先单独写入提交事件，本地却没有可恢复的事务状态，副本又可能比本地多一次扣减。开启 binlog 时，MySQL 用内部两阶段提交协调引擎和 binlog，不是应用把 `COMMIT` 调用两次。

```text
InnoDB redo prepare → Server 写 binlog（按配置同步）→ InnoDB commit
```

| 故障时留下的证据 | 崩溃恢复对这笔未决事务的处理 |
|---|---|
| 引擎已 prepare，有效 binlog 中找不到该事务的完整提交证据 | 回滚，不能只因 redo 存在就当作提交。 |
| 引擎已 prepare，有效 binlog 中已有对应事务的提交证据 | 提交该事务，补上尚未完成的引擎提交步骤。 |

这是简化的内部提交流程，要把“写入进程或系统缓冲区”与“持久化到可靠存储”分开。若希望最大程度降低两边在崩溃中丢失的窗口，关注 `innodb_flush_log_at_trx_commit=1` 和 `sync_binlog=1`，也要有可靠存储保障。组提交可合并同步开销，不代表可以省略提交一致性。

### 面试怎么说
先分别答“向前重做、向后撤销、对外传播”，再用断电卡在 prepare 与 commit 之间的例子说明两个提交证据为什么必须协调。""",
            followups=[
                dict(q="有 binlog，为什么还不能省 redo？", a="binlog 表达要复制或回放的变更事件，不描述 InnoDB 页的恢复细节；引擎仍需要 redo 修复崩溃时尚未刷盘的数据页，并与 undo 配合处理未完成事务。"),
                dict(q="线上调成每秒刷 redo 能承诺只丢一秒吗？", a="不要把定期刷盘频率当成丢失上限。操作系统调度、存储故障类型和 binlog 同步策略都会影响崩溃窗口；这类变更必须明示持久性取舍。"),
            ],
            pitfalls=["认为 redo 存在就是事务已提交，或把 binlog 当作 redo 的副本。", "把两阶段提交说成客户端发两次 COMMIT，或说任何配置下都不会丢数据。"],
            hook="在隔离测试库模拟异常重启，分别记录客户端明确收到提交、明确回滚和结果未知的事务 ID。恢复后核对主库记录、binlog 可回放结果与副本；响应丢失的事务用业务幂等键查最终状态。",
            mnemonic="redo 重做，undo 撤做，binlog 传变更；先准备，再记账，后提交。",
        ),
        dict(
            id="mysql-deep-pagination",
            q="LIMIT 100000, 10 为什么慢？延迟关联与游标分页怎么写？",
            level=2,
            short="`LIMIT 100000, 10` 不是直接跳到第十万行，通常要按顺序产生前 100010 个候选并跳过前 100000 个；还可能排序或回表。要支持跳页，可以先用窄覆盖索引取当页 ID，再关联取宽列；顺序翻页则把上一页最后的排序键传来，按索引从该边界继续。排序键不唯一时带主键作并列裁决。",
            points=[
                "说明 offset 需要扫描或产生并丢弃大量候选，不是按行号跳转",
                "延迟关联先在窄覆盖索引取当页键，再按主键取宽列，仍要走 offset",
                "游标分页通过上页最后复合排序键做索引范围定位，方向与排序一致",
                "相同时间用唯一主键打破并列，并给出稳定排序及谓词示例",
                "比较随机跳页能力与顺序翻页性能，说明并发变更下不等同于一致快照",
            ],
            explain="""### 为什么只返回十行也会扫很多行
如果已经有合适的有序索引，数据库仍没有“第十万零一条满足条件的记录”的快捷地址，通常得走过之前的候选。有过滤时可能检查更多；没有匹配排序的路径时，还可能先做大量排序。下面造 12 万行，同一秒有四条记录，专门验证相同时间的边界。

```sql
CREATE TABLE page_orders (
    id BIGINT PRIMARY KEY, created_at DATETIME NOT NULL,
    detail VARCHAR(200) NOT NULL, KEY idx_created_id (created_at, id)
) ENGINE=InnoDB;
INSERT INTO page_orders (id, created_at, detail)
WITH RECURSIVE seq(n) AS (
    SELECT 0 UNION ALL SELECT n + 1 FROM seq WHERE n < 999
)
SELECT num + 1, TIMESTAMPADD(SECOND, num DIV 4, '2026-01-01 00:00:00'),
       REPEAT('x', 150)
FROM (SELECT aa.n + 1000 * bb.n AS num FROM seq AS aa
      CROSS JOIN seq AS bb WHERE bb.n < 120) AS nums;

SELECT id, created_at, detail FROM page_orders
ORDER BY created_at DESC, id DESC LIMIT 100000, 10;
```

### 方法一：延迟关联，少取宽行
```sql
SELECT oo.id, oo.created_at, oo.detail
FROM (
    SELECT id, created_at FROM page_orders
    ORDER BY created_at DESC, id DESC LIMIT 100000, 10
) AS pp JOIN page_orders AS oo ON oo.id = pp.id
ORDER BY pp.created_at DESC, pp.id DESC;
```

内层有机会只扫 `(created_at, id)` 到所需位置，外层只为选出的十个 ID 取宽列。外层仍显式排序，不依赖派生表的输出顺序。offset 的线性成本还在；如果原查询已被覆盖，或者优化器原本就不逐个取宽列，收益可能很小。若还有状态等筛选，应在内层分页前用同样的条件，并重新评估索引覆盖。

### 方法二：用上一页最后一条的排序键作为游标
```sql
SELECT id, created_at, detail FROM page_orders
WHERE created_at < '2026-01-01 01:23:20'
   OR (created_at = '2026-01-01 01:23:20' AND id < 20001)
ORDER BY created_at DESC, id DESC LIMIT 10;
```

第一屏不带游标；下一屏传回最后一个 `(created_at,id)`。这个边界是本样例第 100000 条有序记录，后续十条与原 offset 查询一致；只比较时间会漏掉同秒但 ID 更小的行。配合索引范围定位才有性能收益，仍要看计划。游标适合下一页，不直接支持第 10001 页这种随机跳转；跨 HTTP 请求也不自动共享快照，最好用不变的排序键并约定并发新增、删除的可见语义。

### 面试怎么说
“延迟关联省的是被跳过记录的宽行读取；游标分页省的是跳过记录这一步。”最后问需求是随机跳页、顺序浏览，还是固定快照导出。""",
            followups=[
                dict(q="为什么要在排序条件里再加 id？", a="同一秒可能有多行，只按时间就无法唯一划分页面，严格小于时间会漏行。用唯一 id 打破并列，比较条件和 ORDER BY 都按同一方向走。"),
                dict(q="用游标就一定不重不漏吗？", a="稳定数据和唯一排序键下可沿边界翻页；并发插入、删除或排序键改变会影响跨请求可见集合。若业务需要固定版本，应另外设计快照或导出方案。"),
            ],
            pitfalls=["认为 LIMIT 会直接定位到 offset 指定的物理行号。", "延迟关联外层不写 ORDER BY，或游标遗漏并列裁决键。"],
            hook="构造同秒多条、空页和结尾不足一页的数据，断言三种写法在固定快照上结果和顺序相同。用并发插入再测协议约定，并画扫描量随页码变化的曲线，不只比较首页耗时。",
            mnemonic="要跳页，先窄后宽；要下一页，带上最后一键。",
        ),
        dict(
            id="mysql-replication-lag",
            q="MySQL 主从复制怎么工作？刚写完却读到旧数据怎么办？",
            level=2,
            short="典型异步复制中，主库把变更写到 binlog；副本接收后落 relay log，再由应用线程重放。主库提交成功不等于副本已执行。用复制状态区分接收慢和应用慢，关键的写后读走主库，或带着本次提交的 GTID 等目标副本应用后再读，超时则回主或按业务降级。半同步确认接收不等于应用完成。",
            points=[
                "说出主库 binlog → 副本接收 → relay log → 应用线程重放",
                "说明异步提交落后可能发生在接收或应用阶段，举出原因",
                "通过复制线程状态、位置或 GTID、延迟指标与心跳定位，不能只看秒数",
                "给出关键读走主库或等待目标 GTID 后读副本的写后读策略",
                "说明等待超时与旧快照的处理，半同步不等于副本已应用",
            ],
            explain="""### 写成功，不等于读副本马上成功
以典型异步主从（源库与副本）复制为例，主库把事务变更写入 binlog；副本接收线程从主库取得事件并写入 relay log，应用线程取出来重放，配置合适时可由多个 worker 并行执行。主库能先响应客户端。某电商修改收货地址，写成功后立即刷新页面却还是旧地址，可能只是读到尚未执行该事务的副本。

### 找到慢在接收还是应用
```sql
SHOW REPLICA STATUS;
```

该命令从 8.0.22 起可用；更早的 8.0 版本用 `SHOW SLAVE STATUS`。查看接收与应用线程是否在跑、最后的错误，以及源与副本的位点；使用 GTID 时可对比已接收和已执行的集合。接收慢先看网络、连接和主库发送；已收未执行则查大事务、锁等待、资源争用或应用并行度。`Seconds_Behind_Source` 只是参考，连不上源或接收本身落后的情况下，它不能证明副本已追平。加一条端到端心跳或用业务标记实测，从源提交到副本能查到要多久，才是读者关心的整体时延。

### 写后读按业务承诺选路
- **关键读回主**：修改成功后的确认页直接读源库，查询使用新事务或新快照。实现直接，代价是主库要承担读压力。
- **等副本执行指定事务**：GTID 模式下取得本次提交的 GTID，传到读侧，在计划读取的同一台副本等待。下面的 UUID 和序号是占位示例，测试时换成真实写事务的 GTID。

```sql
SET @target_gtid = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:42';
SELECT WAIT_FOR_EXECUTED_GTID_SET(@target_gtid, 1) AS wait_result;
```

结果为 0 才表示已经执行目标集合；1 表示超时。失败或超时走主库或明确降级，不要去另一台未经等待的副本碰碰运气。等待成功后用新快照读：在此前建立的 RR 快照里查，仍可能看见旧版本。非关键报表可以接受有界延迟，超过业务阈值摘掉副本或提示数据时间；固定黏主一段时间只是一种近似，不能当作严格保障。

### 面试怎么说
用“收到 relay log”和“应用后读得到”两个水位拆开讲。半同步复制可以改善持久接收保障，但确认收到不是确认应用，因此不能单靠开启半同步解决写后读。""",
            followups=[
                dict(q="Seconds_Behind_Source 为 0，就一定能读到刚写入的数据吗？", a="不能。该值无法证明接收线程已经取到源库最新事件；又有旧快照的影响。需要按业务事务等指定 GTID 或在源库用新快照读。"),
                dict(q="应用线程落后很多，开更多线程就能追上吗？", a="先看是否有并行空间。单个很大的事务、依赖强的事务和热点行锁未必能靠更多线程解决；还要看副本 CPU、磁盘与本地查询争用。"),
            ],
            pitfalls=["把接收 binlog 当成已对读请求可见，或认为半同步能解决所有旧读。", "等待了一个副本却把 SELECT 路由到另一个副本。"],
            hook="在隔离的主副本环境延迟应用线程，先证明成功写后随机读副本会见旧值，再验证回主、等待 GTID 和超时降级三条分支；用心跳标出接收与应用两个水位，避免只断言某个秒数。",
            mnemonic="已提交、已收到、已应用是三个水位。",
        ),
        dict(
            id="mysql-sharding",
            q="什么时候才考虑分库分表，分片键怎么选，代价是什么？",
            level=3,
            short="先确认单库真正撞上写入、容量或维护窗口上限，别按行数定阈值；先试索引、归档、适度升配或读扩展。垂直拆分是按字段或业务边界拆，水平拆分把相同结构的不同行分片。分片键尽量贴合高频查询、分布均匀且稳定，还要准备跨片 join、全局 ID、跨库事务与迁移校验。",
            points=[
                "用写吞吐、容量、维护窗口等指标判断是否需要拆，先排除查询与单点热点问题",
                "区分垂直拆字段或业务和水平拆行，说明分表不必然分散实例压力",
                "分片键选高频访问带得上、分布均匀、不常变且可共置相关数据的列",
                "说明跨片 JOIN、全局查询、分布式 ID 和跨库事务的处理思路与代价",
                "迁移需要对账和灰度切换，扩容要考虑路由变化与数据迁移",
            ],
            explain="""### 什么时候拆，先看瓶颈类型
慢 SQL、糟糕索引或热点单行不会因为多了几张表自动变快。读太重可以先看索引、缓存、读副本，历史数据占空间可先评估归档；持续写入已逼近单实例上限、备份恢复或 DDL 超出维护窗口，且更简单办法已达不到目标时，再考虑拆分。不要用“超过几千万行一律拆”的口号替代压测。

### 垂直与水平怎么选
垂直拆分例子：把订单的大文本详情与高频访问的核心列分两张表，或者按订单和库存业务边界分库。水平拆分例子：同样格式的订单按用户分到不同实例，用户订单列表只访问一片。若只在同一实例内拆表，可能缓和单表维护问题，但 CPU、磁盘和故障域还在同一处。别把实例内分区说成系统已经跨机器分片。

```sql
SELECT MOD(42, 4) AS order_shard, MOD(43, 4) AS next_user_shard;
```

例子是正整数用户 ID 对四取模，42 路由到分片 2；同用户的订单与订单明细按同一个键分，可在一片内 JOIN 和提交。下单查询要带用户 ID；若接口只有订单号，可能需要可路由 ID、独立映射或改接口，不能总扫所有片。热门大客户可能打热一片，得用真实访问分布做压测；把 4 直接改成 8 会改变许多既有键的路由，扩容时可评估固定逻辑桶加路由映射再迁移。

### 复杂性转移到哪里
| 问题 | 可考虑的做法及代价 |
|---|---|
| 跨库 JOIN / 全局排序 | 尽量共置，或用冗余字段、聚合读模型；跨片查询要合并结果，也要处理慢片和部分失败。 |
| 全局 ID | 使用独立发号、带节点的 ID 或合适的全局唯一标识；验证不碰撞、可路由性及索引开销。 |
| 分布式事务 | 尽量将事务边界约束到一片；确实跨库时比较分布式提交和业务补偿，后者不是强一致回滚。 |
| 迁移扩容 | 先回填，追平变更并逐片核数、核关键不变量，再灰度切流；回滚前确认新增写入可被旧路由接住。 |

### 面试怎么说
先答为什么非拆不可，再给一个带上分片键就能单片返回的接口；最后说一个跨片代价和迁移怎样保证不丢不重。""",
            followups=[
                dict(q="用户 ID 和创建时间都能分片，哪个更好？", a="看主路径。用户历史订单按用户共置更合适；按时间容易归档，但最近一段时间可能集中写入同一片。要用查询比例与写入分布作取舍。"),
                dict(q="双写迁移时一边写成功、一边失败怎么办？", a="不能把两次写当原子操作。应明确权威侧，记录可重放且幂等的变更，按水位追平并对账；有差异先修复或阻止切换，避免读写分裂。"),
            ],
            pitfalls=["只按均匀程度选分片键，不问查询是否带上这个键。", "单实例分表后就宣称解决了单实例写上限，或对两套库双写却不对账。"],
            hook="按热点用户、无分片键、跨片查询和分片失联造用例，核对路由、超时、去重及故障降级。迁移前后按分片比行数与关键金额，并对照增量水位和经过灰度的新增写入，不只做全库总量比对。",
            mnemonic="先定位瓶颈，再选访问键；单片好跑，跨片有账。",
        ),
    ],
)
