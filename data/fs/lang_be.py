LANG = [
    dict(id="be1", order=101, track="后端", lang="Go", topic="defer 执行顺序与返回值", kind="output", q="下面 Go 程序会输出什么？注意命名返回值、defer 参数求值和后进先出的执行顺序。",
         code="""package main

import "fmt"

func f() (x int) {
    x = 1
    defer fmt.Println("defer-arg", x)
    defer func() {
        x += 10
        fmt.Println("defer-closure", x)
    }()
    x = 2
    return x + 3
}

func main() {
    fmt.Println("return", f())
}
""",
         answer="""defer-closure 15
defer-arg 1
return 15""",
         explain="""return 语句会先把 x+3 赋给命名返回值 x，此时 x 为 5，然后按后进先出执行 defer。闭包 defer 看到同一个命名返回值，把它改成 15；fmt.Println 的参数在注册 defer 时已经求值为 1。机制能做收尾和修正返回值，但代价是可读性下降，线上建议把指标、锁释放和错误包装写清楚。"""),

    dict(id="be2", order=102, track="后端", lang="Go", topic="slice 底层数组共享与 append 扩容", kind="output", q="下面 Go 程序会输出什么？请关注切片长度、容量和 append 是否复用底层数组。",
         code="""package main

import "fmt"

func main() {
    a := []int{1, 2, 3, 4}
    b := a[:2]
    c := append(b, 9)
    fmt.Println(a, b, c)
    d := append(b, 8, 7, 6)
    d[0] = 100
    fmt.Println(a, b, d)
}
""",
         answer="""[1 2 9 4] [1 2] [1 2 9]
[1 2 9 4] [1 2] [100 2 8 7 6]""",
         explain="""b 的 len 为 2、cap 为 4，第一次 append 一个元素仍在 a 的底层数组内写入，所以 a[2] 变成 9。第二次一次追加 3 个元素超过 b 的容量，运行时分配新数组，之后修改 d[0] 不影响 a。订单明细、库存列表这类切片传递要明确是否允许共享，兜底是 copy 或限制容量 a[:n:n]。"""),

    dict(id="be3", order=103, track="后端", lang="Go", topic="map 引用语义", kind="output", q="下面 Go 程序会输出什么？请说明 map 作为参数传递时哪些修改可见。",
         code="""package main

import "fmt"

func update(m map[string]int) {
    m["paid"]++
    m["new"] = 3
    m = map[string]int{"reset": 9}
    m["paid"] = 100
}

func main() {
    stats := map[string]int{"paid": 1}
    update(stats)
    fmt.Println(stats["paid"], stats["new"], stats["reset"], len(stats))
}
""",
         answer="""2 3 0 2""",
         explain="""map 变量本身是一个描述符，按值传参会复制描述符，但仍指向同一张哈希表，所以函数内对键值的新增和修改对调用方可见。把形参重新赋值为新 map 只改变局部变量，不会让调用方指向新表。高并发统计不能因为 map 是引用语义就直接并发写，必须用锁、分片或 sync.Map，否则会 panic 或数据竞争。"""),

    dict(id="be4", order=104, track="后端", lang="Go", topic="闭包捕获循环变量", kind="output", q="Go 1.22 起，下面程序会输出什么？不要按旧版本循环变量共享的规则作答。",
         code="""package main

import "fmt"

func main() {
    fs := []func(){}
    for _, v := range []int{1, 2, 3} {
        fs = append(fs, func() { fmt.Print(v) })
    }
    for _, f := range fs {
        f()
    }
    fmt.Println()
}
""",
         answer="""123""",
         explain="""Go 1.22 起 range 循环每次迭代会创建新的迭代变量，闭包捕获的是当次迭代的 v，所以输出 123。旧版本常见失败模式是三个闭包共享同一个 v，最后都看到 3。面试追问时要说明版本边界；在兼容老版本、启动 goroutine 或代码审查时，显式写 v := v 仍是低成本兜底。"""),

    dict(id="be5", order=105, track="后端", lang="Go", topic="interface nil 陷阱", kind="output", q="下面 Go 程序会输出什么？注意接口值由动态类型和动态值两部分组成。",
         code="""package main

import "fmt"

type MyErr struct{}

func (e *MyErr) Error() string { return "bad" }

func maybe() error {
    var e *MyErr = nil
    return e
}

func main() {
    err := maybe()
    fmt.Println(err == nil)
    fmt.Printf("%T\\n", err)
}
""",
         answer="""false
*main.MyErr""",
         explain="""接口值只有动态类型和动态值都为空时才等于 nil。maybe 返回的是动态类型 *MyErr、动态值 nil 的 error，因此 err != nil。线上会导致“没有真实错误却进入失败分支”，例如订单回调被错误重试。兜底是函数需要返回 nil 时直接 return nil，或者在赋给接口前判断具体指针是否为空。"""),

    dict(id="be6", order=106, track="后端", lang="Go", topic="channel 关闭与 select", kind="output", q="下面 Go 程序会输出什么？请关注从已关闭 channel 接收时的值和 ok。",
         code="""package main

import "fmt"

func main() {
    ch := make(chan int, 1)
    ch <- 7
    close(ch)
    v1, ok1 := <-ch
    v2, ok2 := <-ch
    fmt.Println(v1, ok1)
    fmt.Println(v2, ok2)
}
""",
         answer="""7 true
0 false""",
         explain="""关闭 channel 不会清空缓冲区，第一次接收先拿到已缓冲的 7，ok 为 true。缓冲耗尽后继续接收会立刻返回元素零值和 ok=false。这个机制适合广播结束信号或消费剩余任务，但不能向已关闭 channel 发送。select 中关闭通道会一直就绪，循环里要把通道置 nil 或退出，避免空转烧 CPU。"""),

    dict(id="be7", order=107, track="后端", lang="Go", topic="goroutine + WaitGroup + Mutex", kind="output", q="下面 Go 程序会输出什么？代码用 WaitGroup 等待并用 Mutex 保护共享计数。",
         code="""package main

import (
    "fmt"
    "sync"
)

func main() {
    var wg sync.WaitGroup
    var mu sync.Mutex
    total := 0
    for i := 0; i < 3; i++ {
        wg.Add(1)
        go func(n int) {
            defer wg.Done()
            mu.Lock()
            total += n
            mu.Unlock()
        }(i + 1)
    }
    wg.Wait()
    fmt.Println(total)
}
""",
         answer="""6""",
         explain="""三个 goroutine 分别累加 1、2、3。WaitGroup 保证主协程等待所有任务完成，Mutex 保证 total 的读改写是互斥的，因此结果确定为 6。没有锁时失败模式是数据竞争和丢更新，压测下库存扣减或计数指标会偶发错误。代价是临界区串行化，热点计数可用分片计数或原子操作优化。"""),

    dict(id="be8", order=108, track="后端", lang="Go", topic="context 取消", kind="output", q="下面 Go 程序会输出什么？请关注 context 取消后 Done 通道和 Err 的行为。",
         code="""package main

import (
    "context"
    "fmt"
)

func main() {
    ctx, cancel := context.WithCancel(context.Background())
    cancel()
    select {
    case <-ctx.Done():
        fmt.Println(ctx.Err())
    default:
        fmt.Println("running")
    }
}
""",
         answer="""context canceled""",
         explain="""调用 cancel 会关闭 ctx.Done 返回的通道，select 立刻进入该分支，Err 返回 context canceled。上下文取消是请求链路的控制信号，适合在订单查询、库存 RPC、数据库查询之间传递超时和取消。代价是所有下游都要主动监听；兜底是给外部调用设置超时、defer cancel，并在日志中记录 request_id、deadline 和取消原因。"""),

    dict(id="be9", order=109, track="后端", lang="Go", topic="error wrapping", kind="output", q="下面 Go 程序会输出什么？请关注 %w 包装后 errors.Is 如何匹配哨兵错误。",
         code="""package main

import (
    "errors"
    "fmt"
)

var ErrStock = errors.New("stock not enough")

func reserve() error {
    return fmt.Errorf("reserve sku failed: %w", ErrStock)
}

func main() {
    err := reserve()
    fmt.Println(errors.Is(err, ErrStock))
    fmt.Println(err)
}
""",
         answer="""true
reserve sku failed: stock not enough""",
         explain="""fmt.Errorf 使用 %w 会保留错误链，errors.Is 能沿链匹配 ErrStock，同时 Error 文本包含外层上下文。这样既能让上层根据错误类型决定返回 409、重试或降级，也能保留排障所需的业务字段。代价是不要滥用字符串比较，兜底是定义清晰的哨兵错误或自定义错误类型，并统一日志字段。"""),

    dict(id="be10", order=110, track="后端", lang="Go", topic="struct 值 / 指针接收者", kind="output", q="下面 Go 程序会输出什么？请区分值接收者和指针接收者对结构体状态的影响。",
         code="""package main

import "fmt"

type Counter struct{ n int }

func (c Counter) AddValue() { c.n++ }
func (c *Counter) AddPointer() { c.n++ }

func main() {
    c := Counter{n: 1}
    c.AddValue()
    fmt.Println(c.n)
    c.AddPointer()
    fmt.Println(c.n)
}
""",
         answer="""1
2""",
         explain="""值接收者会复制 Counter，AddValue 修改的是副本，所以原对象仍为 1。指针接收者拿到原对象地址，AddPointer 修改后原对象变为 2。业务实体如果包含缓存状态、锁或大字段，随意值复制会带来状态不一致或性能浪费。约束是只读小对象可用值接收者，需修改状态或避免复制时用指针接收者。"""),

    dict(id="be11", order=111, track="后端", lang="Go", topic="channel 关闭与 select", kind="choice", q="在订单异步处理服务中，多个 worker 从 jobs channel 消费任务。关于 channel 关闭，哪些说法正确？",
         options=["只有发送方或明确拥有 channel 生命周期的一方应该关闭 channel", "从关闭且已耗尽的 channel 接收会永久阻塞", "向已经关闭的 channel 发送会 panic", "关闭 channel 可以作为广播结束信号，所有接收方都能感知", "接收方为了通知发送方停止，应该直接 close(jobs)"],
         answer=[0, 2, 3],
         explain="""channel 关闭表达“不会再发送新值”，因此通常由发送方或生命周期拥有者关闭。接收方从已关闭且耗尽的 channel 会立即得到零值和 ok=false，不会阻塞；向已关闭 channel 发送会 panic。把关闭当广播结束信号很常见，但多方关闭会引发竞态，兜底是用 context、单独 done channel 或 sync.Once 管理关闭。"""),

    dict(id="be12", order=112, track="后端", lang="Go", topic="context 取消", kind="short", q="设计一个订单查询接口会同时访问 MySQL、Redis 和物流服务。你会怎样使用 context 控制超时、取消和日志排障？",
         answer="""我会在 HTTP 入口为每个请求创建带超时的 context，例如整体 800ms，defer cancel，随后把同一个 context 传给 Redis、MySQL 和物流 RPC。下游必须监听 Done 或使用支持 context 的客户端方法，超时后立即停止等待并释放连接。日志要记录 request_id、user_id、order_id、deadline、ctx.Err()、下游耗时和错误类型，指标按 canceled、deadline_exceeded、业务失败分开统计。兜底策略是对非关键物流轨迹返回降级字段，对库存和支付等关键数据失败则明确返回可重试错误。""",
         points=["入口设置整体 deadline 并 defer cancel", "下游调用使用支持 context 的 API", "区分取消、超时和业务错误", "记录链路字段与各下游耗时", "对关键与非关键数据采用不同降级策略"],
         explain="""context 的价值不是简单传参，而是把调用链生命周期显式传播。约束是电商查询有用户等待时间和连接池容量限制；失败模式是慢下游拖垮线程、连接和 goroutine。机制是 deadline、Done、Err 和日志指标联动，代价是每层都要遵守，否则取消信号无法真正生效。"""),

    dict(id="be13", order=113, track="后端", lang="Go", topic="error wrapping", kind="short", q="库存预占失败时，你会如何设计 Go 的错误类型和错误包装，让 API 层能返回正确状态码且日志可排查？",
         answer="""我会把可判定的业务错误定义成哨兵错误或带字段的自定义错误，例如 ErrStockNotEnough、ErrOrderExpired，并在仓储或领域层用 fmt.Errorf("reserve sku_id=%s qty=%d: %w", skuID, qty, ErrStockNotEnough) 包装。API 层用 errors.Is 或 errors.As 判断错误链，库存不足返回 409 或业务码，参数问题返回 400，未知依赖错误返回 500。日志保留 order_id、sku_id、qty、仓库、错误链和 trace_id，但不要靠字符串 contains 做分支。指标按错误类别计数，便于发现是业务售罄还是系统故障。""",
         points=["定义稳定的哨兵错误或自定义错误类型", "用 %w 保留错误链和上下文", "API 层用 errors.Is/As 映射状态码", "日志包含业务字段和 trace_id", "不要用错误字符串匹配控制流程"],
         explain="""错误设计要服务于控制流和排障两件事。约束是上层需要稳定分类，下层需要携带现场；失败模式是只返回字符串导致状态码、重试和告警全混在一起。包装错误的代价是错误链要有规范，兜底是统一错误码表和中间件记录。"""),

    dict(id="be14", order=114, track="后端", lang="Go", topic="slice 与 map 工程实践", kind="short", q="在大促库存服务中，为什么要特别小心 slice 共享底层数组和 map 并发写？请给出机制、风险和兜底方案。",
         answer="""slice 头部包含指针、长度和容量，截取后可能共享同一底层数组，append 在容量足够时会改到原数组，因此把订单明细切片传给异步逻辑后再复用，可能污染原数据。map 是引用语义，函数内改键值调用方可见，并且普通 map 不支持并发写；多个 goroutine 同时扣减或统计会出现 fatal error 或数据竞争。兜底是跨协程传递前 copy 切片或用 full slice expression 限制容量，map 并发访问用 mutex、分片锁、sync.Map 或把写入串行化，并用 race 检测和压测观察冲突。""",
         points=["说明 slice 头和底层数组共享机制", "说明 append 容量足够时会改原数组", "说明 map 引用语义和并发写风险", "给出 copy、限容、锁或串行化方案", "用 race 检测和压测验证"],
         explain="""这类问题本质是内存别名和并发所有权。约束是高并发下对象会跨层、跨协程传递；失败模式是偶发脏数据、库存错扣或进程 panic。机制清楚后才能选择复制、互斥或所有权转移，代价是在性能和安全之间取舍，并用指标观察锁等待和分配量。"""),

    dict(id="be15", order=115, track="后端", lang="Java", topic="String 常量池与 ==", kind="output", q="下面 Java 程序会输出什么？请区分字符串常量池、new 对象和 intern。",
         code="""public class Main {
    public static void main(String[] args) {
        String a = "order";
        String b = "ord" + "er";
        String c = new String("order");
        System.out.println(a == b);
        System.out.println(a == c);
        System.out.println(a == c.intern());
    }
}
""",
         answer="""true
false
true""",
         explain="""编译期常量拼接会直接进入字符串常量池，所以 a 和 b 指向同一对象。new String 会在堆上创建新对象，a == c 比较引用为 false。intern 返回常量池中的规范引用，所以 a == c.intern() 为 true。业务代码比较订单状态、渠道码必须用 equals，不能用 ==，否则不同来源构造出的相同文本会走错分支。"""),

    dict(id="be16", order=116, track="后端", lang="Java", topic="Integer 缓存", kind="output", q="下面 Java 程序会输出什么？请关注自动装箱和 IntegerCache 默认范围。",
         code="""public class Main {
    public static void main(String[] args) {
        Integer a = 127;
        Integer b = 127;
        Integer c = 128;
        Integer d = 128;
        System.out.println(a == b);
        System.out.println(c == d);
        System.out.println(c.equals(d));
    }
}
""",
         answer="""true
false
true""",
         explain="""Integer.valueOf 默认缓存 -128 到 127 的对象，自动装箱 127 时 a 和 b 复用缓存引用，所以 == 为 true。128 默认不在缓存范围内，会创建不同对象，== 为 false，但 equals 比较数值为 true。金额、库存、页码等包装类型不能用 == 判断业务相等，兜底是用 equals 或先拆箱，同时注意 null 拆箱会触发 NPE。"""),

    dict(id="be17", order=117, track="后端", lang="Java", topic="finally 与 return", kind="output", q="下面 Java 程序会输出什么？请说明 finally 对返回值的影响。",
         code="""public class Main {
    static int f() {
        int x = 1;
        try {
            return x;
        } finally {
            x = 2;
            System.out.println("finally " + x);
        }
    }
    public static void main(String[] args) {
        System.out.println("return " + f());
    }
}
""",
         answer="""finally 2
return 1""",
         explain="""try 中 return 会先把返回值 1 保存起来，然后执行 finally。finally 把局部变量 x 改成 2 并打印，但没有重新 return，因此最终返回已保存的 1。若 finally 里再 return，会覆盖原返回值并吞掉异常，这是线上排障的大坑。资源释放建议用 try-with-resources，避免在 finally 里写复杂控制流。"""),

    dict(id="be18", order=118, track="后端", lang="Java", topic="静态初始化顺序", kind="output", q="下面 Java 程序会输出什么？请按静态字段和静态代码块的文本顺序分析。",
         code="""public class Main {
    static int a = init("a", 1);
    static int b;
    static {
        System.out.println("block " + a + " " + b);
        b = 3;
    }
    static {
        b = init("b", 2);
    }
    static int init(String name, int value) {
        System.out.println(name + "=" + value);
        return value;
    }
    public static void main(String[] args) {
        System.out.println("main " + a + " " + b);
    }
}
""",
         answer="""a=1
block 1 0
b=2
main 1 2""",
         explain="""类加载准备阶段会把静态字段设为默认值，所以 block 中能看到 b 的默认值 0。初始化阶段按源码顺序执行：先 a=1，再静态块打印并把 b 设为 3，随后字段初始化 b=2 覆盖前值，最后 main 打印 1 和 2。配置注册、单例和缓存预热不要依赖隐晦顺序，兜底是显式初始化方法和启动自检。"""),

    dict(id="be19", order=119, track="后端", lang="Java", topic="多态与重载解析", kind="output", q="下面 Java 程序会输出什么？请区分重载的编译期选择和重写的运行期分派。",
         code="""public class Main {
    static class Animal {}
    static class Dog extends Animal {}
    static class Service {
        void handle(Animal a) { System.out.println("animal"); }
        void handle(Dog d) { System.out.println("dog"); }
    }
    static class SpecialService extends Service {
        @Override void handle(Animal a) { System.out.println("special animal"); }
    }
    public static void main(String[] args) {
        Animal x = new Dog();
        Service s = new SpecialService();
        s.handle(x);
    }
}
""",
         answer="""special animal""",
         explain="""重载方法在编译期根据变量静态类型选择，x 的静态类型是 Animal，因此选择 handle(Animal)。运行期再根据接收者真实类型 SpecialService 做重写分派，执行 special animal。策略路由、消息处理器如果依赖参数真实类型但只写重载，可能不会命中预期分支，兜底是显式策略表、instanceof 模式匹配或访问者模式。"""),

    dict(id="be20", order=120, track="后端", lang="Java", topic="集合 fail-fast", kind="output", q="下面 Java 程序会输出什么？请关注增强 for 中修改 ArrayList 的行为。",
         code="""import java.util.*;

public class Main {
    public static void main(String[] args) {
        List<Integer> xs = new ArrayList<>(List.of(1, 2, 3));
        try {
            for (Integer x : xs) {
                if (x == 2) xs.add(4);
            }
            System.out.println("done");
        } catch (ConcurrentModificationException e) {
            System.out.println("fail-fast");
        }
        System.out.println(xs.size());
    }
}
""",
         answer="""fail-fast
4""",
         explain="""ArrayList 迭代器记录 expectedModCount，增强 for 迭代过程中直接调用 xs.add 会改变 modCount，下一次迭代检查时抛 ConcurrentModificationException。异常不代表修改回滚，4 已经加入列表，所以 size 为 4。批量处理订单时要用 Iterator.remove、收集后统一修改或 CopyOnWriteArrayList，不能把 fail-fast 当并发安全保证。"""),

    dict(id="be21", order=121, track="后端", lang="Java", topic="equals/hashCode 约定", kind="output", q="下面 Java 程序会输出什么？类重写了 equals 但没有重写 hashCode。",
         code="""import java.util.*;

public class Main {
    static class OrderKey {
        String id;
        OrderKey(String id) { this.id = id; }
        public boolean equals(Object o) {
            return o instanceof OrderKey k && Objects.equals(id, k.id);
        }
    }
    public static void main(String[] args) {
        Set<OrderKey> set = new HashSet<>();
        set.add(new OrderKey("A"));
        System.out.println(set.contains(new OrderKey("A")));
        System.out.println(set.size());
    }
}
""",
         answer="""false
1""",
         explain="""HashSet 先用 hashCode 定位桶，再在桶内用 equals 比较。OrderKey 没有重写 hashCode，两个内容相同的新对象通常使用不同的 Object hashCode，contains 会去另一个桶查找，结果为 false。业务键对象、缓存 key 和去重集合必须同时重写 equals 与 hashCode，并保持参与计算的字段不可变，否则会出现重复扣费或去重失效。"""),

    dict(id="be22", order=122, track="后端", lang="Java", topic="volatile 与 synchronized", kind="choice", q="关于 Java 中 volatile 和 synchronized 在并发订单状态刷新中的作用，哪些说法正确？",
         options=["volatile 能保证变量写入对其他线程可见", "volatile 能让 count++ 变成原子操作", "synchronized 既提供互斥，也提供进入和退出临界区的可见性语义", "对复合不变式，如库存数量和版本号同时更新，通常需要锁或原子类组合", "volatile 一定比 synchronized 正确且性能更好"],
         answer=[0, 2, 3],
         explain="""volatile 主要提供可见性和禁止特定重排序，不能让读改写的 count++ 自动原子化。synchronized 提供互斥，并通过 monitor enter/exit 建立 happens-before 关系。若要同时维护库存数量、版本号和状态，约束是复合不变式必须一起更新，单个 volatile 不够。性能要结合竞争程度和临界区大小测试，不能绝对化。"""),

    dict(id="be23", order=123, track="后端", lang="Java", topic="线程池参数", kind="short", q="大促期间订单导出任务突然堆积。请说明 Java 线程池 corePoolSize、maximumPoolSize、queue、keepAliveTime、拒绝策略如何影响系统，并给出排查指标。",
         answer="""ThreadPoolExecutor 的执行顺序通常是先用 corePoolSize 承接任务，核心线程满后进队列，队列满后再扩到 maximumPoolSize，仍无法接收时触发拒绝策略。无界队列会让 maximumPoolSize 基本失效，失败模式是内存上涨和任务延迟不可控；过小队列加过大最大线程会导致上下文切换和下游数据库被打爆。排查时看 activeCount、poolSize、queueSize、completedTaskCount、rejectedCount、任务耗时分位数、下游连接池等待和 CPU 使用率。兜底是分离快慢任务、限流、降级导出范围、设置有界队列和可观测的拒绝策略。""",
         points=["解释核心线程、队列、最大线程的触发顺序", "指出无界队列和过大线程数的失败模式", "说明 keepAliveTime 对非核心线程回收的作用", "列出队列长度、拒绝数、耗时和下游等待指标", "给出限流、隔离、降级和有界队列方案"],
         explain="""线程池不是把参数调大就安全，核心约束是 CPU、内存和下游容量。机制决定了排队、扩容和拒绝的时机；代价是在吞吐、延迟和资源之间权衡。线上要用指标闭环，而不是凭经验改数。"""),

    dict(id="be24", order=124, track="后端", lang="Java", topic="JVM 内存区域与 GC", kind="short", q="一个 Java 订单服务出现频繁 Full GC 和接口 P99 抖动，你会如何从 JVM 内存区域、对象分配和 GC 日志角度排查？",
         answer="""我会先确认堆、元空间、线程栈和直接内存的使用情况，重点看老年代占用、晋升速率、大对象分配和 Full GC 前后回收比例。命令上用 jcmd VM.native_memory、GC.heap_info、jstat -gcutil、jmap histogram 或在线 profiler，结合 GC 日志看 pause 时间、触发原因、晋升失败、humongous allocation、元空间扩容等。若 Full GC 后老年代下降很少，优先怀疑缓存无界、静态集合、监听器未释放或批量查询一次加载过多。修复要限制缓存容量、分页处理、减少临时对象、调整堆和 GC 参数，并用 QPS、P99、分配速率和 GC 暂停时间验证。""",
         points=["区分堆、元空间、栈和直接内存", "分析老年代、晋升、大对象和回收比例", "使用 jcmd、jstat、jmap 或 profiler", "结合 GC 日志定位触发原因", "用容量限制、分页和参数调整闭环验证"],
         explain="""Full GC 对在线交易的直接影响是停顿和尾延迟。约束是对象生命周期和内存区域不同，失败模式也不同。机制上要看分配速率、晋升和可回收性；代价是调参可能掩盖泄漏，所以必须同时做代码层修复和指标验证。"""),

    dict(id="be25", order=125, track="后端", lang="Java", topic="Spring 事务传播 / AOP 代理", kind="short", q="在 Spring 服务中，为什么同一个类里 this.inner() 调用带 @Transactional 的方法可能不生效？REQUIRED 和 REQUIRES_NEW 在订单场景中有什么差异？",
         answer="""Spring 声明式事务通常通过代理实现，外部调用进入代理后才会织入事务拦截器。同一个类内部用 this.inner() 调用绕过代理，inner 方法上的 @Transactional 可能不生效，表现为异常后没有回滚或传播行为不符合预期。REQUIRED 会加入当前事务，没有事务就新建，适合订单主流程保持原子性；REQUIRES_NEW 会挂起外层事务并开启新事务，适合审计日志、失败记录等需要独立提交的动作。代价是新事务会多占连接，且内外事务一致性要设计清楚。兜底是拆到另一个 Bean、通过代理调用、写集成测试并检查事务日志。""",
         points=["说明 Spring AOP 代理拦截边界", "指出 self-invocation 绕过代理", "区分 REQUIRED 加入或新建事务", "区分 REQUIRES_NEW 挂起外层并独立提交", "给出拆 Bean、代理调用和集成测试兜底"],
         explain="""事务问题常见失败模式不是注解写错，而是调用路径没有经过代理。约束是订单写库需要明确原子边界；机制是代理、传播行为和连接绑定；代价是独立事务增加连接占用和一致性复杂度。"""),

    dict(id="be26", order=126, track="后端", lang="Java", topic="equals/hashCode 约定", kind="short", q="把订单号封装成 OrderKey 作为 HashMap 的 key 时，equals/hashCode 应遵守哪些约定？如果 key 字段可变会有什么线上风险？",
         answer="""equals 要满足自反、对称、传递、一致以及与 null 比较返回 false，hashCode 要保证 equals 为 true 的对象必须有相同 hashCode。HashMap 先根据 hashCode 找桶，再用 equals 比较，所以只重写 equals 不重写 hashCode 会导致同一订单号查不到。作为 key 的字段应尽量不可变，如果放入 Map 后修改 orderNo，原对象所在桶不变但新 hash 指向别处，后续 get、remove 和去重都可能失败。线上风险是重复处理订单、缓存击穿或幂等表失效。兜底是使用不可变类、final 字段、构造时校验，并为 key 类写集合行为单测。""",
         points=["列出 equals 基本约定", "说明 equals 与 hashCode 的一致性要求", "解释 HashMap 先定位桶再比较", "说明可变 key 导致查找和删除失败", "给出不可变类和单测兜底"],
         explain="""集合键的正确性是幂等和缓存的基础。约束是哈希容器依赖稳定 hash；失败模式是内容相同却查不到，或修改 key 后对象遗失在旧桶。机制理解清楚后，应从类型设计上避免可变键。"""),

    dict(id="be27", order=127, track="后端", lang="Java", topic="集合 fail-fast", kind="short", q="Java 集合的 fail-fast 是什么？它能不能作为并发安全机制？在遍历订单列表时要删除或追加元素应怎么做？",
         answer="""fail-fast 是很多集合迭代器在发现结构性修改次数 modCount 与期望值不一致时，尽快抛 ConcurrentModificationException 的机制。它用于暴露错误用法，不保证一定抛出，也不是并发安全机制；多线程下即使没抛异常也可能读到不一致数据。遍历时删除当前元素应使用 Iterator.remove，批量删除可用 removeIf，追加元素通常先收集到临时列表再统一 addAll。多读少写场景可考虑 CopyOnWriteArrayList，但写入代价高。真正并发访问要使用并发集合、锁或把修改限制在单线程。""",
         points=["定义 fail-fast 和 modCount 检查", "说明它不是并发安全保证", "给出 Iterator.remove/removeIf 方案", "说明追加元素应延后批量处理", "区分 CopyOnWriteArrayList 的适用场景"],
         explain="""fail-fast 的目标是快速失败，而不是保护数据。约束是集合迭代有结构稳定性要求；失败模式是遍历中修改导致异常或遗漏。机制上应选择正确的修改入口，代价是在内存复制、锁竞争和实现复杂度之间权衡。"""),

    dict(id="be28", order=128, track="后端", lang="Java", topic="volatile 与 synchronized", kind="short", q="请用库存扣减的例子说明 volatile、synchronized、AtomicInteger 分别适合什么场景，以及应该观察哪些并发指标。",
         answer="""volatile 适合保存开关、配置版本这类单变量可见性状态，例如活动是否开启；它不能保证 stock-- 的复合操作原子性。synchronized 适合保护库存数量、冻结数量、版本号等需要一起维护的不变式，能提供互斥和可见性，但竞争高时会增加阻塞。AtomicInteger 适合单个数值的 CAS 更新，例如简单计数器，冲突高时会自旋重试。库存扣减通常还要结合数据库条件更新或分布式锁，避免多实例内存计数不一致。指标应看成功率、冲突重试次数、锁等待时间、接口 P99、数据库 update affected rows 和超卖告警。""",
         points=["说明 volatile 适合可见性开关", "说明 synchronized 保护复合不变式", "说明 AtomicInteger 适合单变量 CAS", "指出多实例还需数据库或分布式一致性", "列出冲突、锁等待、P99 和 affected rows 指标"],
         explain="""并发工具要按共享状态的约束选择。失败模式是把可见性当原子性，或只解决单机内存而忽略多实例。机制和代价不同：锁会阻塞，CAS 会重试，数据库条件更新会增加存储压力。"""),

    dict(id="be29", order=129, track="后端", lang="Python", topic="可变默认参数", kind="output", q="下面 Python 程序会输出什么？请关注默认参数对象的创建时机。",
         code="""def add(item, bucket=[]):
    bucket.append(item)
    return bucket

print(add("a"))
print(add("b"))
print(add("c", []))
print(add("d"))
""",
         answer="""['a']
['a', 'b']
['c']
['a', 'b', 'd']""",
         explain="""默认参数在函数定义时求值一次，bucket=[] 会被后续未传 bucket 的调用共享。因此 a、b、d 进入同一个列表，而显式传入 [] 的 c 使用新列表。接口参数、缓存列表和表单字段不能使用可变默认值，否则请求之间串数据。兜底写法是 bucket=None，函数内部再创建新列表。"""),

    dict(id="be30", order=130, track="后端", lang="Python", topic="作用域与闭包", kind="output", q="下面 Python 程序会输出什么？请关注闭包 late binding 和默认参数捕获。",
         code="""funcs = []
for i in range(3):
    funcs.append(lambda: i)
print([f() for f in funcs])

funcs2 = []
for i in range(3):
    funcs2.append(lambda i=i: i)
print([f() for f in funcs2])
""",
         answer="""[2, 2, 2]
[0, 1, 2]""",
         explain="""Python 闭包捕获变量名而不是当时的值，循环结束后 i 为 2，第一组 lambda 调用时都读取同一个 i，所以得到三个 2。第二组通过默认参数 i=i 在定义时把当前值绑定到函数默认值中，因此得到 0、1、2。批量生成任务回调、路由处理器或测试用例时要小心，兜底是默认参数或工厂函数。"""),

    dict(id="be31", order=131, track="后端", lang="Python", topic="生成器", kind="output", q="下面 Python 程序会输出什么？请关注生成器的惰性执行和 StopIteration。",
         code="""def gen():
    print("start")
    yield 1
    print("middle")
    yield 2

it = gen()
print("created")
print(next(it))
print(next(it))
try:
    print(next(it))
except StopIteration:
    print("done")
""",
         answer="""created
start
1
middle
2
done""",
         explain="""调用 gen() 只创建生成器对象，不会执行函数体，所以先输出 created。每次 next 执行到下一个 yield 暂停，先打印 start 再产出 1，第二次打印 middle 再产出 2。耗尽后抛 StopIteration，被捕获后打印 done。生成器适合流式处理大文件和分页数据，代价是只能单向消费，排障时要注意数据何时真正被读取。"""),

    dict(id="be32", order=132, track="后端", lang="Python", topic="装饰器", kind="output", q="下面 Python 程序会输出什么？请关注装饰器在函数定义时执行，wrapper 在调用时执行。",
         code="""def deco(fn):
    print("decorate", fn.__name__)
    def wrapper(*args, **kwargs):
        print("before")
        result = fn(*args, **kwargs)
        print("after")
        return result
    return wrapper

@deco
def pay(x):
    print("pay", x)
    return x * 2

print("call")
print(pay(3))
""",
         answer="""decorate pay
call
before
pay 3
after
6""",
         explain="""@deco 在函数定义完成后立即执行，相当于 pay = deco(pay)，所以先输出 decorate pay。真正调用 pay(3) 时执行 wrapper，打印 before，调用原函数输出 pay 3，随后打印 after 并返回 6。鉴权、事务和埋点装饰器都依赖这个机制，代价是包装后元数据可能丢失，工程上应使用 functools.wraps 保留函数名和注解。"""),

    dict(id="be33", order=133, track="后端", lang="Python", topic="GIL", kind="short", q="Python 的 GIL 对 Web 后端有什么影响？CPU 密集型和 I/O 密集型任务应该如何选型？",
         answer="""GIL 是 CPython 解释器中保护对象内存管理的一把全局锁，使同一进程内多个 Python 线程不能同时执行 Python 字节码。对 I/O 密集型 Web 请求，线程或 asyncio 在等待网络、磁盘、数据库时会释放或让出执行权，仍能提高并发；对 CPU 密集型任务，如图片处理、复杂特征计算，多线程通常不能线性加速，可能还增加切换开销。兜底方案是用多进程、任务队列、C 扩展释放 GIL 或把计算拆到专门服务。指标要看 CPU 利用率、run queue、请求 P99、线程数、上下文切换和队列积压。""",
         points=["说明 GIL 限制同进程多线程执行字节码", "区分 I/O 密集型和 CPU 密集型", "给出 asyncio、线程、多进程或任务队列选择", "说明 C 扩展或独立服务可绕开限制", "列出 CPU、P99、队列和上下文切换指标"],
         explain="""GIL 不是“Python 不能并发”，而是限制 CPU 并行执行字节码。约束来自任务类型；失败模式是用线程池跑 CPU 任务导致延迟更差。机制清楚后才能把 Web 请求、后台任务和计算服务拆开。"""),

    dict(id="be34", order=134, track="后端", lang="Python", topic="浅深拷贝", kind="short", q="请解释 Python 浅拷贝和深拷贝的区别，并说明在订单明细、优惠列表这类嵌套结构中如何避免串改。",
         answer="""浅拷贝会创建新的外层容器，但内层对象仍与原对象共享；深拷贝会递归复制可复制的内层对象。订单对象如果包含 items 列表、每个 item 又包含优惠列表，使用 copy.copy 后修改某个明细的优惠，原订单和拷贝订单可能同时变化，导致试算价污染正式价格。兜底是对需要隔离的嵌套字段使用 copy.deepcopy，或用不可变数据结构、dataclass replace、显式构造 DTO。深拷贝代价是耗时和内存增加，还可能遇到循环引用或不可复制资源，因此要按字段选择，并用单测覆盖修改后互不影响。""",
         points=["说明浅拷贝只复制外层容器", "说明深拷贝递归复制内层对象", "结合嵌套订单结构说明串改风险", "给出 deepcopy、不可变对象或显式 DTO 方案", "说明性能和资源复制代价"],
         explain="""拷贝问题本质是对象别名。约束是嵌套结构在试算、回滚和缓存中经常复用；失败模式是一个流程修改影响另一个流程。机制决定了隔离层级，代价是在安全性和性能之间权衡。"""),

    dict(id="be35", order=135, track="后端", lang="Web 框架", topic="RESTful 资源命名", kind="choice", q="为电商订单与物流轨迹设计 RESTful API，哪些路径和方法更符合资源建模？",
         options=["GET /orders/123", "POST /createOrder", "GET /orders/123/traces", "PATCH /orders/123/status", "GET /getOrderById?id=123"],
         answer=[0, 2, 3],
         explain="""RESTful 更强调资源和统一方法语义，订单是 /orders/{id}，轨迹是订单下的子资源 /orders/{id}/traces，局部更新状态可用 PATCH。/createOrder 和 /getOrderById 把动作塞进路径，导致缓存、权限和文档难统一。代价是资源建模前期要想清边界，兜底是用 OpenAPI 固化路径、方法、状态码和错误结构。"""),

    dict(id="be36", order=136, track="后端", lang="Web 框架", topic="状态码与幂等方法", kind="short", q="订单创建、支付回调、取消订单、查询订单分别适合哪些 HTTP 方法和状态码？如何保证幂等？",
         answer="""创建订单通常用 POST /orders，成功返回 201 和 Location，重复提交可用 Idempotency-Key 或业务请求号去重。支付回调可用 POST /payments/callbacks，但必须以第三方流水号或支付单号做幂等，重复通知返回 200 表示已处理。取消订单可用 POST /orders/{id}/cancel 或 PATCH /orders/{id}/status，若设计成 PUT 某个确定取消资源也可以幂等；已取消再次取消应返回 200 或 204 而不是重复扣库存。查询订单用 GET /orders/{id}，成功 200，不存在 404，无权限 403。指标要看重复请求命中率、409 冲突数和幂等表延迟。""",
         points=["说明 POST 创建及 201/Location", "说明 GET 查询及 200/404/403", "说明取消订单的状态语义", "说明回调按流水号幂等", "列出 Idempotency-Key、业务号或幂等表方案"],
         explain="""HTTP 方法语义影响缓存、重试和客户端预期。约束是网络会超时、网关会重试、用户会重复点击；失败模式是重复下单、重复退款或库存错回。机制是用稳定幂等键和状态机判断，代价是需要额外存储和冲突处理。"""),

    dict(id="be37", order=137, track="后端", lang="Web 框架", topic="分页与过滤", kind="short", q="商家工作台订单列表如何设计分页、排序和过滤参数？offset 分页和游标分页各有什么代价？",
         answer="""订单列表可以设计 GET /orders?seller_id=...&status=PAID&created_from=...&created_to=...&sort=-created_at&limit=50&cursor=...。offset 分页简单，适合后台小数据量跳页，但深分页会扫描和丢弃大量行，并且新订单插入时容易重复或漏数据。游标分页用 created_at+id 这类稳定排序键生成 cursor，性能稳定且适合无限滚动，但不方便任意跳页，客户端也要保存游标。过滤字段必须与索引匹配，limit 要有上限，例如 100，响应返回 next_cursor、total 是否精确要说明，指标看慢查询、扫描行数和缓存命中。""",
         points=["给出过滤、排序、limit、cursor 参数", "说明 offset 深分页扫描和漂移问题", "说明游标分页稳定但不便跳页", "强调稳定排序键 created_at+id", "说明 limit 上限和索引匹配"],
         explain="""分页设计是接口层和数据库层的共同约束。失败模式是深分页拖垮数据库，或数据变化导致重复漏单。机制上用稳定排序和索引减少扫描，代价是牺牲任意跳页能力。"""),

    dict(id="be38", order=138, track="后端", lang="Web 框架", topic="中间件 / 拦截器链", kind="short", q="请描述 Web 框架中中间件或拦截器链的执行模型，并说明鉴权、限流、日志、异常处理应该如何排序。",
         answer="""中间件通常按注册顺序进入，调用 next 后进入后续中间件和业务处理，返回时再按相反顺序执行收尾逻辑，类似洋葱模型。通用异常恢复应放最外层，确保后续 panic 或异常能转换成统一响应；请求日志和 trace 也应靠外层生成 request_id 并统计总耗时。限流可在鉴权前做 IP 粗限，也可在鉴权后按用户或商家限流；鉴权应早于业务处理，避免未授权访问。响应压缩、指标上报、审计日志根据是否需要看到最终状态放在 next 之后。代价是顺序错误会导致日志缺字段、异常漏捕或限流维度不准。""",
         points=["说明洋葱模型和 next 前后顺序", "异常恢复与 trace/log 靠外层", "鉴权早于业务处理", "限流可按 IP 或身份选择位置", "说明顺序错误的失败模式"],
         explain="""中间件链把横切逻辑放到统一层。约束是每层依赖的字段不同；失败模式是未生成 trace 就打日志，未鉴权就查库，或异常绕过统一响应。机制清楚后才能安排顺序和兜底。"""),

    dict(id="be39", order=139, track="后端", lang="Web 框架", topic="鉴权 JWT vs Session", kind="short", q="JWT 和 Session 鉴权有什么区别？在商家工作台和开放 API 场景下如何选择，并如何处理登出和权限变更？",
         answer="""Session 通常在服务端保存登录态，客户端只拿 session id，优点是可集中失效、权限变更立即生效，缺点是需要共享存储或粘性会话。JWT 把声明签名后交给客户端，服务端可无状态校验，适合开放 API、跨服务调用和读多场景，但令牌签发后在过期前难撤销，不能放敏感信息。商家工作台如果强调登出、封禁和权限实时变化，可用 Session 或短期 access token 加服务端 refresh token；开放 API 可用短期 JWT 加 key 管理和签名。兜底是设置较短过期、维护黑名单或 token_version，并在网关记录 subject、tenant、scope 和失败原因。""",
         points=["比较服务端状态和无状态校验", "说明 Session 易撤销但依赖共享存储", "说明 JWT 易扩展但撤销困难", "结合工作台和开放 API 选择", "给出短期 token、黑名单或 token_version 兜底"],
         explain="""鉴权选择取决于撤销实时性、扩展性和安全边界。失败模式是 JWT 长期有效导致离职账号仍可访问，或 Session 存储故障导致全站登录失败。机制和代价都要在方案中说明。"""),

    dict(id="be40", order=140, track="后端", lang="数据库", topic="事务隔离级别与 MVCC", kind="short", q="请解释 MySQL InnoDB 在订单扣库存场景中，读已提交和可重复读的差异，以及 MVCC 能解决和不能解决什么问题。",
         answer="""InnoDB 通过 undo log 和 Read View 实现 MVCC，让普通一致性读不阻塞写。读已提交下每条语句创建新的 Read View，同一事务两次查询可能看到其他事务已提交的新结果；可重复读下通常事务内第一条一致性读创建 Read View，后续看到同一快照，避免不可重复读。MVCC 解决的是快照读一致性，不自动解决扣库存的写写冲突和业务超卖。库存扣减应使用 update sku set stock=stock-? where id=? and stock>=?，检查 affected rows，必要时配合行锁、版本号或唯一幂等记录。指标看锁等待、死锁、事务时长和更新失败率。""",
         points=["说明 Read View 和 undo log", "区分读已提交和可重复读快照时机", "说明 MVCC 解决快照读不阻塞", "指出不能自动解决写写冲突", "给出条件更新、行锁、版本号和幂等方案"],
         explain="""隔离级别要和业务写入机制一起看。失败模式是以为可重复读就不会超卖，实际快照读不等于库存扣减的原子校验。机制上必须在写 SQL 的 where 条件中表达约束，并用 affected rows 兜底。"""),

    dict(id="be41", order=141, track="后端", lang="数据库", topic="索引失效", kind="choice", q="下面哪些写法可能导致 MySQL 无法有效使用普通 B+Tree 索引或只能使用部分索引？",
         options=["where date(created_at) = '2026-10-29'", "where seller_id = 10 and status = 'PAID'", "where phone like '%1234'", "where amount + 1 > 100", "where created_at >= '2026-10-29 00:00:00' and created_at < '2026-10-30 00:00:00'"],
         answer=[0, 2, 3],
         explain="""对索引列使用函数 date(created_at) 或表达式 amount+1，会让普通索引难以按原值有序查找；前导通配 like '%1234' 也无法利用 B+Tree 的前缀有序性。等值 seller_id/status 通常可用联合索引，时间范围用半开区间能利用 created_at 索引。兜底是改写谓词、建函数索引或冗余可索引字段，并用 EXPLAIN 看 type、key 和 rows。"""),

    dict(id="be42", order=142, track="后端", lang="数据库", topic="慢查询分析 EXPLAIN", kind="short", q="订单列表接口慢查询，你会如何使用 EXPLAIN 分析，并结合哪些运行时指标判断优化是否有效？",
         answer="""我会先拿到真实慢 SQL、绑定参数和表数据量，再执行 EXPLAIN 或 EXPLAIN ANALYZE。重点看访问类型 type 是否从 ALL/range 变成 ref/const，key 是否命中预期联合索引，rows 和 filtered 是否过大，Extra 是否出现 Using filesort、Using temporary、Using where。还要检查 where 条件是否满足联合索引最左前缀，排序字段是否能被索引覆盖，select 列是否可以用覆盖索引。优化后不能只看执行计划，要用真实参数压测或灰度观察平均耗时、P95/P99、扫描行数、buffer pool 命中、CPU、锁等待和错误率。""",
         points=["获取真实 SQL、参数和数据量", "检查 type、key、rows、filtered、Extra", "分析最左前缀、排序和覆盖索引", "使用 EXPLAIN ANALYZE 或真实压测", "用耗时分位数、扫描行数、CPU 和锁等待验证"],
         explain="""EXPLAIN 是定位访问路径的工具，不是最终业务验收。约束是优化器选择受数据分布和参数影响；失败模式是开发库计划很好、生产仍慢。机制上要把执行计划和运行时指标闭环。"""),

    dict(id="be43", order=143, track="后端", lang="数据库", topic="分库分表", kind="short", q="订单表按用户或订单号分库分表时，需要考虑哪些字段、路由、查询和扩容问题？",
         answer="""分库分表首先要确定分片键，订单详情按 order_id 查询多，可用 order_id 路由；用户订单列表按 user_id 查询多，可按 user_id 分片或维护用户订单索引表。分片键必须出现在高频查询条件中，否则会广播查询。全局唯一订单号要包含时间、分片信息或使用独立发号器；跨分片事务要尽量避免，通过本地事务、消息最终一致和幂等补偿处理。扩容要考虑一致性哈希、双写迁移、历史数据回填和灰度读切换。指标看路由命中率、广播查询次数、单分片容量、热点分片、迁移延迟和补偿失败数。""",
         points=["选择与高频查询匹配的分片键", "说明订单详情和用户列表的不同路由", "避免广播查询和跨分片事务", "设计全局订单号和幂等补偿", "考虑扩容迁移、热点和监控指标"],
         explain="""分库分表解决容量和写入压力，但会牺牲单库查询和事务便利性。失败模式是分片键选错导致所有查询广播，或扩容时双写不一致。机制上要把路由、ID、事务和迁移方案一起设计。"""),

    dict(id="be44", order=144, track="后端", lang="数据库", topic="Redis 数据结构与持久化", kind="short", q="在库存缓存、排行榜、物流轨迹和延迟任务中，你会选择哪些 Redis 数据结构？RDB 和 AOF 的取舍是什么？",
         answer="""库存缓存可用 String 保存数量并配合 Lua 做原子校验扣减，商品热度排行榜可用 ZSET 按分数排序，物流轨迹可用 List 或 Stream 追加事件，延迟任务可用 ZSET 以执行时间为 score 扫描到期任务。Hash 适合保存订单摘要或商家配置的多个字段。持久化方面，RDB 是周期性快照，恢复快、文件紧凑，但两次快照之间可能丢数据；AOF 记录写命令，数据丢失窗口更小，但文件更大，重写和 fsync 策略会影响延迟。关键库存不能只依赖 Redis，兜底是数据库最终校验、消息补偿、过期策略和缓存命中率、内存、evicted_keys、持久化耗时监控。""",
         points=["按库存、排行、轨迹、延迟任务选择结构", "说明 String、Hash、List/Stream、ZSET 用法", "比较 RDB 快照和 AOF 追加日志", "指出 Redis 不能作为唯一库存真相", "列出命中率、内存淘汰和持久化指标"],
         explain="""Redis 选型要从访问模式出发。约束是每种结构的时间复杂度和一致性边界不同；失败模式是用缓存当强一致库存，宕机或淘汰后数据丢失。持久化降低风险但带来延迟和恢复成本。"""),

    dict(id="be45", order=145, track="后端", lang="Linux", topic="CPU 排查命令", kind="short", q="线上订单服务 CPU 突然打满，你会用哪些 Linux 命令逐层定位？请说明每个命令看什么。",
         answer="""我会先用 top 或 htop 看整机 CPU、load average、哪个进程占用高，以及 user、system、iowait 的比例。再用 top -H -p <pid> 找到高 CPU 线程，把线程 id 转成十六进制后关联 Java jstack 或 Go pprof。vmstat 1 看 run queue、上下文切换、系统态和用户态变化，判断是计算、锁竞争还是系统调用过多。perf top 或进程 profiler 可看热点函数；strace -p <pid> -c 可粗看系统调用是否异常频繁。排查要同时记录时间、版本、QPS、P99 和错误率，避免把正常流量上涨误判为代码死循环。""",
         points=["用 top/htop 定位进程和 CPU 类型", "用 top -H 定位线程", "用 vmstat 看队列和上下文切换", "用 perf、pprof、jstack 或 strace 找热点", "结合 QPS、P99、版本和错误率判断"],
         explain="""CPU 排查要从整机到进程、线程、函数逐层收敛。约束是 CPU 高可能来自计算、锁、自旋、系统调用或流量增长；失败模式是只重启不留证据。机制和指标结合才能决定限流、回滚还是代码修复。"""),

    dict(id="be46", order=146, track="后端", lang="Linux", topic="内存 / 磁盘排查命令", kind="short", q="服务出现 OOM 或磁盘写满告警时，你会用哪些 Linux 命令定位内存和磁盘问题？",
         answer="""内存方面先用 free -h 看可用内存和 swap，top 按内存排序找进程，ps aux --sort=-rss 看 RSS 排名，pmap -x <pid> 或语言运行时工具看地址空间分布，dmesg -T | grep -i oom 查看是否被内核 OOM killer 杀掉。磁盘方面用 df -h 看文件系统容量和 inode，df -i 看 inode 是否耗尽，du -xh --max-depth=1 从大目录逐层下钻，lsof | grep deleted 查已删除但仍被进程占用的文件。iostat -x 1 看磁盘 util、await 和队列，判断是容量满还是 I/O 饱和。兜底是清理可删除日志、扩容、限制日志速率并补上轮转策略。""",
         points=["内存用 free、top、ps、pmap、dmesg", "磁盘容量用 df、du、df -i", "检查 deleted open file", "用 iostat 判断 I/O 饱和", "给出日志轮转、清理和扩容兜底"],
         explain="""内存和磁盘问题都要区分容量耗尽、泄漏和瞬时压力。失败模式是删除大日志后空间不释放，因为文件仍被进程打开；或只看 df 忽略 inode。命令链要能定位责任进程和目录，再做低风险处置。"""),

    dict(id="be47", order=147, track="后端", lang="Linux", topic="网络排查命令", kind="short", q="订单服务访问支付或物流下游超时，你会如何用 ss、lsof、curl、tcpdump 等命令排查网络问题？",
         answer="""我会先用 curl -v 或 nc 检查域名解析、连接建立、TLS 握手和首字节耗时，确认是连接不上、握手慢还是响应慢。ss -tanp 查看到下游地址的 ESTABLISHED、SYN-SENT、TIME-WAIT 数量，判断连接池耗尽、半连接堆积或端口耗尽。lsof -i -p <pid> 可以看进程打开的 socket 和目标地址。若怀疑丢包或重传，用 tcpdump 按 host/port 抓包，再结合 mtr 或 ping 看路径质量。排查必须带上目标域名、IP、端口、超时时间、错误码和时间窗口，避免把下游 5xx、DNS、网络 ACL 或本机端口耗尽混为一谈。""",
         points=["用 curl/nc 区分 DNS、连接、TLS 和响应慢", "用 ss 查看连接状态和端口压力", "用 lsof 关联进程 socket", "用 tcpdump/mtr/ping 分析丢包和路径", "记录目标、端口、错误码和时间窗口"],
         explain="""网络超时不是单一原因。约束是请求要经过 DNS、连接、TLS、网关和下游服务；失败模式是只看应用日志无法区分哪一段慢。命令要按链路层次拆解，并和连接池指标、下游状态码一起判断。"""),

    dict(id="be48", order=148, track="后端", lang="Linux", topic="日志检索 grep / awk", kind="short", q="大促后需要统计 10 分钟内订单创建失败的主要错误码。请给出 grep/awk 思路，并说明日志检索的注意事项。",
         answer="""如果日志是文本行并包含时间、接口、error_code、order_id，可以先用 grep '2026-10-29 20:1' app.log | grep 'POST /orders' | grep 'create_failed' 缩小范围，再用 awk 提取 error_code 字段并聚合，例如 awk -F'error_code=' '{print $2}' | awk '{print $1}' | sort | uniq -c | sort -nr。JSON 日志优先用 jq 提取字段，避免正则误切。注意按实例和滚动文件补全范围，处理时区、跨分钟、采样、重复日志和 trace_id 去重。结果要同时给失败总数、各错误码数量、占比和样例 trace_id，便于继续下钻数据库或下游依赖。""",
         points=["用 grep 先按时间、接口和关键字缩小范围", "用 awk/sort/uniq 聚合 error_code", "JSON 日志优先用 jq", "注意多实例、滚动文件、时区和去重", "输出数量、占比和样例 trace_id"],
         explain="""日志检索要把文本处理和业务语义结合。约束是日志量大、多实例且格式可能不一致；失败模式是漏掉滚动文件或重复统计重试日志。机制上先过滤再结构化提取，代价是临时命令易错，长期应沉淀到日志平台和指标。"""),
]
