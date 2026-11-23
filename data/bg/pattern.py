CHAPTER = dict(
    id="pattern",
    order=10,
    name="设计模式",
    blurb="从三类模式摸底，到用模式拆解测试框架",
    map="""| 板块 | 必会问题 | 一句话答案 |
|---|---|---|
| 摸底 | 你知道哪些设计模式？ | 创建型管对象怎么来，结构型管对象怎么接，行为型管对象怎么协作。 |
| 创建 | 单例、工厂、建造者怎么选？ | 单例约束实例数量，工厂选具体实现，建造者分步组装复杂对象。 |
| 结构 | 适配器、装饰器、代理都在包装，差在哪？ | 适配器换接口，装饰器叠能力，代理管访问。 |
| 行为 | 策略、模板方法、责任链怎么区分？ | 策略选一个算法，模板规定骨架，责任链让多个节点依次处理或截断。 |
| 通知 | 观察者与发布订阅如何区分？ | 看主体是否直接持有并通知观察者，还是只往中间通道发布事件。 |
| 设计原则 | SOLID 能解决什么？ | 它是一组判断边界是否清晰的原则，不是要求把每段代码都抽成接口。 |
| 测开实战 | 用例、页面和数据怎么分层？ | 用例表达业务预期，Page Object 封装页面动作，工厂或 Builder 准备数据。 |

**复习顺序**：先把三类各讲两个，不急着背全名单；再用“测试环境客户端怎么建、断言怎么换、结果怎么通知”练习工厂、策略和观察者。最后把包装类和流程类各做一次对比，挑一个真项目按“原来哪里痛 → 怎么拆 → 怎么测改动收益”复述。设计模式不是考类图记忆；能说明什么不变、什么在变，以及何时不值得引入，才算能用。""",
    cards=[
        dict(
            id="pattern-overview",
            q="你知道哪些设计模式？能按三大类举例吗？",
            level=1,
            short="我按解决的问题分三类。创建型管对象怎么来：单例限制实例数量，工厂方法把产品选择交给子类，建造者分步组装复杂对象。结构型管怎么拼：适配器转换接口，装饰器叠加能力，代理控制访问。行为型管怎么协作：策略替换算法，观察者一对多通知，模板方法固定流程骨架。比如测试平台里，工厂选客户端，策略选断言，观察者收集运行结果。",
            points=["说出创建型、结构型、行为型及各自要解决的问题", "创建型至少举两例并逐个说明用途", "结构型至少举两例并区分换接口、增强、访问控制", "行为型至少举两例并区分替换算法、通知、固定流程", "把至少一个模式落到具体测试场景或说明引入成本"],
            explain="""### 别从背名单开始，从变化开始
测试平台起初只跑一种环境，直接建客户端就行。后来加本地模拟、集成环境，构造分支散落在每个用例里；与此同时，报告和告警也开始改用例主体。不同变化挤进一个函数，改一处就容易打坏另一处。设计模式是针对这类重复出现的变化，把职责分给不同对象的做法，不是必须照搬的框架。

### 三类各记三个
| 类别 | 你要回答什么 | 示例和用途 |
|---|---|---|
| 创建型 | 谁有权创建，何时创建，怎么组装？ | 单例保持一个作用域内唯一实例；工厂方法由子类决定具体产品；建造者把复杂组装拆成步骤。 |
| 结构型 | 现有对象怎样接到一起？ | 适配器翻译接口；装饰器在原接口外叠能力；代理在原接口外控制是否、何时访问。 |
| 行为型 | 工作怎么分配，消息怎么传？ | 策略从可替换算法中选一个；观察者让一个状态变化通知多个订阅者；模板方法固定步骤顺序。 |

### 串成一次测试运行
```text
运行器 ── 创建 ──> 环境工厂返回客户端
用例   ── 调用 ──> 计时装饰器包裹客户端并转发请求
用例   ── 断言 ──> 按任务类型选严格相等或范围比较
运行器 ── 完成 ──> 通知报告组件与统计组件
```
这里工厂不决定断言，断言策略不创建客户端，报告也不该偷偷改用例结果。只看代码有时都是“把事情交给另一个对象”，要看它负责哪类变化：工厂返回可用对象；策略给相同输入按某个算法算出判定；观察者收到事件后各做独立处理。一个模块可以同时用多种模式，三大类不是互斥的文件夹。

### 面试怎么说
先用“创建、组合、协作”立三根柱子，各点名两三个并加动词，再挑你熟悉的业务讲改动前后。比如原来所有接口测试手写环境地址，现在只在入口选客户端；验证时让同一份用例切换环境，并确认用例层不再依赖地址与认证细节。如果只有一个稳定实现，直接构造和传参往往更省；不要为了展示模式把三行直白代码变成三个只会转发的类。""",
            followups=[dict(q="工厂和策略都能用字典注册，怎么区分？", a="看调用者得到什么：工厂把创建细节藏起来，常返回客户端或测试数据；策略让已有流程选择具体算法，通常直接消费输入并产生结果。实现都用字典也不改变职责。"), dict(q="用了模式怎么证明不是过度设计？", a="拿一项真实变更验证，比如新增环境只动构造入口和对应测试，用例不改。若没有第二种变化、抽象还增加了理解成本，先保留直接写法。")],
            pitfalls=["只报模式名字，说不出每种管什么", "看到委托就给代码贴标签，不分析哪部分变化"],
            hook="用一个你维护过的测试仓库练习：圈出实例创建、客户端包装、用例运行三个边界，选一个最常改的点做小重构。用新增一个环境或一种报告作为验收，不以新加了几个类作为成绩。",
            mnemonic="对象怎么来、怎么接、怎么一起干。",
        ),
        dict(
            id="pattern-singleton",
            q="单例模式是什么？Python 和 Java 怎么写线程安全的单例？",
            level=1,
            short="单例在约定作用域内只创建一个实例，并提供同一个入口。Python 优先用模块级对象；要延迟创建，可以用锁保护 `__new__` 的检查、初始化和发布，或用带锁的类装饰器缓存对象，别忘了 `__init__` 可能重复执行。Java 可用双重检查锁加 volatile、静态内部类或枚举。实例唯一不等于实例里的数据线程安全，更不等于跨进程唯一。",
            points=["说出约定作用域内实例唯一，不承诺跨进程唯一", "说明 Python 模块级对象利用正常导入的模块缓存", "说明锁覆盖检查、构造与发布，并防止 __init__ 重复初始化", "说出装饰器缓存实例及替换类名的代价", "Java 说出 DCL 内外两次检查与 volatile 安全发布，以及静态内部类、枚举", "区分创建线程安全与共享可变状态线程安全"],
            explain="""### 意图：只共享一份对象，不把共享状态自动变安全
比如同一测试进程想读取一份固定配置，反复解析既浪费又可能读到不同版本。最简单的办法是在配置模块顶层建一次，正常用同名导入时复用模块缓存；多进程、重复执行模块或重载都不能拿这个保证当分布式锁。例子用不可变配置，避免共享字典被用例随手写坏。

```python
from types import MappingProxyType

SETTINGS = MappingProxyType({"region": "test"})
assert SETTINGS["region"] == "test"
```

### Python 延迟建：锁住检查到发布
```python
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

class Registry:
    _lock = Lock()
    _instance = None

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance.names = ("smoke",)
                cls._instance = instance
            return cls._instance

with ThreadPoolExecutor(max_workers=4) as pool:
    instances = list(pool.map(lambda _: Registry(), range(16)))
assert all(item is instances[0] for item in instances)
```
构造失败就不发布。例子不设计继承扩展，也不写有副作用的 `__init__`：`__new__` 返回该类的实例后，正常构造调用仍会进入 `__init__`。不能指望 GIL 把“判断、初始化、赋值”合成一步。替代写法是把锁和缓存装进闭包：

```python
from functools import wraps
from threading import Lock

def singleton(cls):
    lock = Lock()
    instance = None

    @wraps(cls)
    def get():
        nonlocal instance
        with lock:
            if instance is None:
                instance = cls()
            return instance
    return get

@singleton
class Reporter:
    pass

assert Reporter() is Reporter()
```
上面仅支持无参构造，装饰后的 `Reporter` 是函数而不是类，不能当 `isinstance` 的类参数或照常继承。锁也不保护返回后对对象字段的修改；客户端能否跨线程共享要看其契约。

### Java：三种写法各靠什么
```java
final class Registry {
    private static volatile Registry instance;
    private Registry() {}
    static Registry get() {
        if (instance == null) {
            synchronized (Registry.class) {
                if (instance == null) instance = new Registry();
            }
        }
        return instance;
    }
}

final class HolderRegistry {
    private HolderRegistry() {}
    private static class Holder {
        static final HolderRegistry INSTANCE = new HolderRegistry();
    }
    static HolderRegistry get() { return Holder.INSTANCE; }
}

enum EnumRegistry { INSTANCE }
```
外层检查避免每次加锁，内层检查防止排队的两个线程重复构造；`volatile` 的写读建立 happens-before，让读到非空引用的线程也看到构造结果（构造时不要提前泄露 `this`）。内部类在首次主动使用其字段时初始化，靠类初始化同步；枚举用一个常量表达唯一性，也适用类初始化规则。这里的 Java 唯一性依赖同一个类定义，不能跨类加载器或进程承诺唯一。

### 面试怎么说
先说复用作用域和安全发布，再说共享对象不等于共享状态安全。工厂决定建哪种对象，不保证只建一个；测试里如果只是想在一次运行复用资源，优先考虑显式依赖注入或合适作用域的 fixture，这比全局单例好替换、好清理。""",
            followups=[dict(q="为什么锁住 __new__ 还会重复初始化？", a="每次通过类名构造都会先调用 __new__，它返回所属类实例后还会照常执行 __init__；应该把一次性初始化和发布放进同一临界区，或改用工厂入口。"), dict(q="Java 双重检查能只加 volatile 不加锁吗？", a="不能，volatile 让写入安全可见，但不会把检查和创建合成原子操作；两个线程都可能看到空引用，各建一个。锁内检查负责避免重复创建。"), dict(q="并行执行的用例应该共享一个客户端吗？", a="不一定。核对客户端的线程安全约定和登录态；按账户、环境或执行 worker 隔离实例。配置可以共享不可变快照，连接的释放交给生命周期管理。")],
            pitfalls=["把 GIL 当作跨多步构造、发布的锁", "用单例承诺跨多个测试进程只启动一次任务", "只验证对象身份，不验证初始化次数和共享状态"],
            hook="测开验证时让多个线程在同一屏障后同时取实例，不仅断言对象身份相同，还统计初始化次数并检查对象完整。多进程下改查每个执行 worker 是否正确隔离配置、账号与资源。",
        ),
        dict(
            id="pattern-factory",
            q="简单工厂、工厂方法、抽象工厂有什么区别？",
            level=1,
            short="工厂把创建细节从使用方挪走。简单工厂用一个函数按参数选实现；工厂方法由基类定义创建入口，子类决定一种产品的具体实现；抽象工厂提供多个创建入口，产出彼此匹配的一族产品。测试里我会先用简单工厂按环境选客户端；环境还要求鉴权和数据成套变化时，再考虑抽象工厂，不会一开始就写一堆子类。",
            points=["说出调用方依赖产品契约而非具体构造参数", "简单工厂使用条件分支或注册表集中选择产品", "工厂方法由子类覆写创建方法选择具体产品", "抽象工厂创建同一变体下多个匹配产品", "用环境客户端或数据工厂举例并说明抽象的升级时机"],
            explain="""### 意图：让使用方不必知道对象怎么创建
一份用例在本地读模拟结果，在集成环境发请求。如果每条用例都写环境判断、拼地址、读凭据，新增环境时就得改很多处。让客户端暴露同一个 `ping` 接口，在入口选实现，用例只接收客户端。

### 同一例子看三种工厂
```python
class LocalClient:
    def ping(self):
        return {"ok": True, "env": "local"}

class IntegrationClient:
    def ping(self):
        return {"ok": True, "env": "integration"}

def make_client(env):
    return {"local": LocalClient, "integration": IntegrationClient}[env]()

class SmokeSuite:
    def make_client(self):
        raise NotImplementedError

    def run(self):
        return self.make_client().ping()["ok"]

class LocalSuite(SmokeSuite):
    def make_client(self):
        return LocalClient()

class EnvironmentFactory:
    def client(self):
        raise NotImplementedError

    def user(self):
        raise NotImplementedError

class LocalFactory(EnvironmentFactory):
    def client(self):
        return LocalClient()

    def user(self):
        return {"tenant": "local", "name": "demo"}

class IntegrationFactory(EnvironmentFactory):
    def client(self):
        return IntegrationClient()

    def user(self):
        return {"tenant": "integration", "name": "demo"}

assert make_client("integration").ping()["ok"]
assert LocalSuite().run()
for factory in (LocalFactory(), IntegrationFactory()):
    assert factory.client().ping()["env"] == factory.user()["tenant"]
```
这里用假客户端演示契约，不打真实服务。第一种只是“查表后构造”，加环境改注册处，简单工厂不属于经典三大类清单里的独立模式名称。第二种 `SmokeSuite` 可跑固定冒烟流程，但创建步骤交给子类；并非方法只要叫 `create` 就是工厂方法。第三种一次选择一个环境工厂，再分别造客户端、用户数据；环境也可能以后有匹配的鉴权器，产品族的价值是不混用。生产实现应对未知环境尽早失败，不默默回退到真实环境。

### 对比与面试话术
工厂方法多了一层继承，适合调用骨架已经存在、变动点集中在创建的情形；抽象工厂新增一套环境容易，但新增一个所有环境都需要的产品类型，要改整组工厂。建造者则解决“同一个复杂对象怎么一步步填好”，并不以选产品族为目标。回答时先讲“选实现、让子类决定、选一族”，再说项目只出现一个维度变化时一个函数已经足够。""",
            followups=[dict(q="数据工厂和 Builder 怎么搭配？", a="数据工厂提供常见有效默认值或按场景挑数据类型；当测试需要叠加许多可选字段和约束时，可让工厂返回预设 Builder，再在用例里显式覆盖重要字段。"), dict(q="实际怎么测试不同环境的客户端工厂？", a="针对每个环境检查地址、凭据来源和匹配的数据命名空间，再用同一套契约用例验证实现的输入输出；另测未知环境明确失败，切勿因此误向生产发请求。")],
            pitfalls=["把任何带 create 名字的静态函数叫作工厂方法模式", "只因返回多个对象就叫抽象工厂，忘了产品要成套匹配"],
            hook="接口框架可在 fixture 中根据已校验的环境构造客户端，再注入契约用例。数据工厂要另测默认值、显式覆盖与唯一命名；错误环境选择应在测试执行前报错，不能静默切换。",
        ),
        dict(
            id="pattern-strategy",
            q="策略模式怎么消除一串 if-else？能举个测试例子吗？",
            level=1,
            short="策略模式把一组可替换算法放在同一个调用约定下，主流程只负责选择和调用，不写每种算法的细节。Python 里常用 `dict` 注册函数：严格相等、延迟不超过阈值是不同断言策略，也可以按渠道选不同通知实现。它不是让条件凭空消失，而是集中选择，并把算法分支从主流程拿出去。",
            points=["说出一组可替换算法和相同的调用约定", "用字典注册、按键选择并调用函数", "说明只是集中选择逻辑，不是消除所有条件", "区分策略选择一个算法、模板方法固定步骤、观察者通知多方", "用断言或通知渠道举例，并处理未知策略"],
            explain="""### 意图：让主流程稳定，让算法独立变化
跑完接口用例之后要做断言：状态码精确相等，RT 不高于阈值，有些字段只检查是否包含。把每种判断写在执行器结尾，很快会多出一串分支。这里检查规则不一样，但都接收实际值和期望值并给判定；统一的输入输出就是策略的接缝，不用为了它写一套继承体系。

### 最小例子：让注册表选择断言算法
```python
def equals(actual, expected):
    return actual == expected

def at_most(actual, expected):
    return actual <= expected

def contains(actual, expected):
    return expected in actual

CHECKS = {"eq": equals, "max": at_most, "contains": contains}

def verify(rule, actual, expected):
    if rule not in CHECKS:
        raise ValueError(f"未知断言规则: {rule}")
    if not CHECKS[rule](actual, expected):
        raise AssertionError(f"{rule}: 实际 {actual!r}，期望 {expected!r}")

verify("eq", 200, 200)
verify("max", 85, 100)
verify("contains", {"order_id": 1}, "order_id")
```
给执行器增加一种近似相等策略，只注册函数，不改 `verify` 的失败语义。例子里一个条件验证配置、一个条件报告失败，这两个条件应该保留；目标是集中分发，不是比赛删除 `if`。真实平台会定义参数类型、单位和失败信息，不能拿毫秒值跟秒阈值直接比较，也要避免把含密钥的实参打印到报告。

### 取舍：同样的动作，变化点不同
工厂的选择结果是客户端或别的产品，策略的选择结果是当前要执行的算法。模板方法固定流程并让子类填步骤，策略把行为作为函数或对象注入，通常更方便在同一个执行器上切换。选邮件或站内信之一是策略；某事件同时让邮件组件和报告组件都处理，更像观察者。只有两条清晰稳定的规则时，一个 `if` 反而更直观；经常新增规则或需要独立测试时，注册表才值回维护成本。

### 面试怎么说
按“谁选择、约定是什么、加规则改哪里”说明。举个细节：把未知规则在加载用例时就报错，平台 CI 为每种规则跑通过、失败和非法输入。这样不仅分支短了，还能证明没把错误配置悄悄当成成功。""",
            followups=[dict(q="不用类还能叫策略模式吗？", a="可以，关键是算法能按同一契约替换，客户端或配置能决定使用哪个。需要携带状态或生命周期时可以用对象，无状态的规则用函数通常更清楚。"), dict(q="多个规则要求同时成立怎么办？", a="执行器可以按列表组合多个已注册策略，显式规定全部通过还是任意通过、是否短路和如何汇总失败；这是组合策略，不是让各规则暗自调用下一个。")],
            pitfalls=["把未知策略默认成通过或无条件回退", "把不同单位或不兼容的输入硬塞给同一契约"],
            hook="用规则表给几个团队复用同一测试执行器。单测每条断言的通过、边界、拒绝及错误信息，再测执行器未知 key 保持失败和报告脱敏，防止新规则让既有用例被误判通过。",
        ),
        dict(
            id="pattern-observer",
            q="观察者和发布订阅有什么区别？pytest hook 属于哪类思路？",
            level=1,
            short="观察者是一对多通知：主体保存观察者或回调，状态变了就直接通知。发布订阅多一层事件通道：发布者只把事件发给总线或主题，由通道找到订阅者。是否同步不是本质区别。pytest hook 用于运行生命周期扩展，框架在约定时机调插件，可类比通知，但它也可能收集结果或控制流程，不等同消息队列。",
            points=["观察者主体维护并直接通知观察者", "发布订阅由中间通道匹配主题与订阅者", "区分有无中间通道与同步异步，二者互不等价", "pytest hook 举例用于报告收集，并说明不承诺消息队列语义", "说明通知的异常隔离或跨进程重复投递处理"],
            explain="""### 意图：一处变化通知多个独立的接收方
用例结束后要写报告、统计用时，还可能通知值班。若运行器直接逐个调用这些组件，加一个统计项也得改执行核心。观察者把接收方放进主体维护的列表，主体只知道通知约定。发布订阅再抽掉这份直接关系：运行器知道主题和事件格式，不知道谁订阅了它。

### 同一个测试结果的两种递送方式
```python
from collections import defaultdict

class Run:
    def __init__(self):
        self.observers = []

    def finish(self, case):
        for callback in tuple(self.observers):
            callback(case)

class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)

    def subscribe(self, topic, callback):
        self.subscribers[topic].append(callback)

    def publish(self, topic, event):
        for callback in tuple(self.subscribers.get(topic, ())):
            callback(event)

report, metrics = [], []
run = Run()
run.observers.append(report.append)
run.finish("login")
bus = EventBus()
bus.subscribe("case.finished", report.append)
bus.subscribe("case.finished", metrics.append)
bus.publish("case.finished", "search")
assert report == ["login", "search"] and metrics == ["search"]
```
两段都是同步派发，差别仍然成立：`Run` 拿着回调，事件发布者只需要拿到 `bus`。快照遍历可防止本轮遍历被回调增删列表扰动，不提供线程安全。实际要设计取消订阅、订阅顺序、异常是否中断；例子默认异常向上传递，若报告失败不能影响测试判定，应显式隔离并留下错误证据。跨进程再考虑事件 ID、幂等、积压、顺序与投递保证，不能因为叫总线就承诺不丢不重。

### pytest hook 的边界与面试话术
比如在插件实现 `pytest_runtest_logreport(report)`，根据 `report.when` 区分 setup、call、teardown 并汇总结果；不能把每条 report 都当一个完成的用例。框架调度已注册的插件实现，像进程内的生命周期通知。某些 hook 还可以返回结果或包裹调用，所以不能笼统说 pytest hook 就是纯事件广播。最后做对比：策略是选谁来做，责任链可能中途停，通知则通常让多个接收方各自处理。""",
            followups=[dict(q="发布订阅一定要上消息队列吗？", a="不需要，进程内事件总线也能按主题同步派发；有跨进程、持久化、削峰或独立消费要求时才考虑消息中间件，并明确能容忍怎样的重复和延迟。"), dict(q="报告组件挂了，测试结果该怎么记录？", a="把测试判定和报告传输区分开；报告线程或订阅者失败时持久化原始结果、暴露投递失败并可重试，重试按用例运行 ID 去重，避免吞掉主测试结果。")],
            pitfalls=["用同步或异步作为唯一区分条件", "没考虑回调报错阻断后续通知或重复注册"],
            hook="给测试平台插件做两组验证：同一事件能被统计和报告同时收到；一个订阅者失败后另一个是否继续，要符合明确约定。聚合结果时专测 setup 失败、正常 call 和 teardown 失败。",
        ),
        dict(
            id="pattern-decorator",
            q="装饰器模式和 Python 的装饰器语法是一回事吗？",
            level=2,
            short="不是一回事。装饰器模式的意图是保持被包装对象的主要接口，通过组合和转发叠加能力，比如给测试客户端叠计时和结果采集。Python 的 `@` 是定义时应用并重新绑定对象的语法；它能表达函数包装，也能只做注册或换掉类，不一定是装饰器模式。适配器重点是换接口，代理重点是管访问。",
            points=["装饰器模式保持接口并通过组合叠加能力", "内外对象都实现相同调用契约，可以多层包装", "写出 @decorate 对应 func = decorate(func) 的含义", "说明只注册不包装时未必是装饰器模式", "按意图区分装饰器、适配器和代理"],
            explain="""### 意图：不动原实现，一层层加能力
接口测试有时要记录请求的开销，有时要额外收集调用次数；这些不是客户端本身的业务职责。如果每种组合都做一个子类，就会得到“计时客户端”“计时加统计客户端”等重复实现。装饰器持有一个实现相同接口的对象，调用时把请求交给内部对象，并在前后加行为。因为外层仍能当客户端用，可以按需要再套一层。

### Python 最小例子：包对象与包函数
```python
from functools import wraps
from time import perf_counter

class Client:
    def get(self, path):
        return {"path": path, "status": 200}

class TimedClient:
    def __init__(self, inner, samples):
        self.inner, self.samples = inner, samples

    def get(self, path):
        start = perf_counter()
        try:
            return self.inner.get(path)
        finally:
            self.samples.append(perf_counter() - start)

samples = []
client = TimedClient(Client(), samples)
assert client.get("/health")["status"] == 200 and len(samples) == 1

calls = []

def traced(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        calls.append(func.__name__)
        return func(*args, **kwargs)
    return wrapped

@traced
def health():
    return "ok"

assert health() == "ok" and calls == ["health"]
```
第一段没有用 `@`，却是装饰器模式。第二段用 `@traced` 表达包装，等价于定义后把 `health` 绑定为 `traced(health)` 的结果；`wraps` 保留名称等元信息并设置 `__wrapped__`，不负责保证行为兼容。若另一个 `@register` 只把函数记到用例表再原样返回，这是注册用途，并没有给调用叠加能力。

### 对比与面试话术
适配器把 `fetch()` 换成框架需要的 `get()`；装饰器仍给调用方一个 `get()` 并多记一次用时；代理可在真正调用前判定是否允许访问。同样是包对象，按目的区分而不是看类图硬归类。多层叠加还要谈顺序：计时放重试外层记录总耗时，放内层记录每一次尝试。面试时说清保留了哪条契约、叠加了什么行为、怎么测顺序和异常，别只回答“就是 `@`”。""",
            followups=[dict(q="多个 @ 叠起来，哪个先包？", a="最靠近函数定义的装饰器先应用；写成上面 @outer、下面 @inner，最终相当于 outer(inner(func))。真正调用时通常先进入外层，再由外层调用内层。"), dict(q="采集指标失败，要让原调用失败吗？", a="视契约而定；普通观测逻辑应隔离失败并暴露采集异常，不要覆盖原业务异常。若是明确要求阻断的审计，应约定失败策略并为它单独写测试。")],
            pitfalls=["所有使用 @ 的代码都说成对象装饰器模式", "包装后吞异常或替换返回值，破坏原有契约"],
            hook="把计时封装成可选客户端层，用同一契约测试直接客户端和包装客户端。分别检查成功与超时时的返回或异常一致，并验证装饰层顺序变化时总耗时和单次耗时没有混算。",
        ),
        dict(
            id="pattern-proxy",
            q="什么是代理模式？静态代理、动态代理和 AOP 怎么联系？",
            level=2,
            short="代理让调用方经由一个相同接口访问真实对象，由代理决定要不要、什么时候、用哪条路径调用。静态代理手写转发方法，动态代理运行期集中拦截并转发；AOP 是把日志、审计等横切逻辑集中施加到匹配调用点，代理是实现手段之一。测试里可代理一个接口客户端，记录调用、对明确可重试的操作加重试，或转发到假后端。",
            points=["代理保持主要调用契约，控制真实对象访问", "静态代理显式手写转发，动态代理运行期集中拦截", "解释 AOP 是横切思想且不只靠代理实现", "用测试客户端日志、幂等重试或 Mock 路由举例", "按控制访问与增强功能区分代理和装饰器"],
            explain="""### 意图：让调用方不直接控制真实对象怎么被访问
同一个测试任务可能连集成环境，也可能走假后端，平台还想在真正发请求前检查运行模式。调用方仍用 `get(path)`，不需要自己判断目标与记录轨迹；代理可以限入、延迟创建目标或选择后端。重点是访问决策，不是把新能力叠给用户。

### 最小例子：显式转发与运行时拦截
```python
class RealClient:
    def get(self, path):
        return (200, "real", path)

class FakeClient:
    def get(self, path):
        return (200, "fake", path)

class RoutingProxy:
    def __init__(self, real, fake, offline):
        self.target = fake if offline else real

    def get(self, path):
        return self.target.get(path)

class LoggingProxy:
    def __init__(self, target, calls):
        self.target, self.calls = target, calls

    def __getattr__(self, name):
        member = getattr(self.target, name)
        if not callable(member):
            return member

        def invoke(*args, **kwargs):
            self.calls.append(name)
            return member(*args, **kwargs)
        return invoke

calls = []
client = LoggingProxy(RoutingProxy(RealClient(), FakeClient(), True), calls)
assert client.get("/health") == (200, "fake", "/health")
assert calls == ["get"]
```
`RoutingProxy` 手写 `get` 入口，配置离线就从不触达真实后端；两个后端在例子里都不联网。`LoggingProxy` 通过普通属性访问的后备入口解析目标方法，运行时给它加拦截。这个教学写法不等价于全透明代理，例如 `len(proxy)` 等特殊方法查找不走该转发。Java 中可通过基于接口的 `Proxy` 和 `InvocationHandler` 表达类似的动态分派，不代表所有代理都自动支持任意类或内部自调用。

### 对比与面试话术
代理侧的 AOP 把共用的日志或审计逻辑写在拦截入口，调用必须确实经过代理，目标直接调用自己的另一个方法可能绕过它。单纯的计时层按意图也可以叫装饰器；拦截访问或切换目标更能说明代理。重试是有条件的访问控制：仅重试明确允许的操作或有幂等保证的业务写入，限制次数、纳入总预算，不能把所有异常都重发。面试时按“谁持有接口 → 在何处拦截 → 哪些调用不会被拦截”讲，再补一个不能盲目重试的例子。""",
            followups=[dict(q="代理和 Mock 是一回事吗？", a="不是。代理是控制访问的结构，可以转真实目标，也可以按模式选假后端；Mock 是测试替身，常验证具体调用交互，它不一定持有或转发到真实对象。"), dict(q="如何确认超时重试没有创建两笔订单？", a="模拟服务已受理但响应丢失，重试复用同一幂等键，在允许的重试窗口内检查接口结果、订单持久化数量和代理记录，证明请求尝试多次而业务效果只有一次。")],
            pitfalls=["认为动态代理对任意属性和内部调用都生效", "每次遇到异常都重试所有写请求，忽略幂等和预算"],
            hook="代理客户端测试要查记录的调用顺序和实际后端命中次数。离线模式断言真实后端零次；可重试读取断言达到次数后停止。错误报告仅留可关联的标识，不记录凭据与完整敏感请求。",
        ),
        dict(
            id="pattern-template",
            q="模板方法模式是什么？测试用例的执行骨架怎么写？",
            level=2,
            short="模板方法在基类固定算法骨架，允许子类只填某些步骤，例如按 setup、run、assert、teardown 执行测试。基类用 `try/finally` 让失败也进入清理，并约定 setup 部分成功如何回收。它控制的是步骤的顺序，策略控制的是某一步用什么算法。现代 Python 测试也常用 fixture 和组合提供同样的生命周期约束。",
            points=["基类方法固定执行顺序，变化步骤由子类实现", "覆盖 setup、run、assert、teardown 四阶段", "使用 finally 并考虑 setup 部分成功或清理失败", "区分继承式流程骨架和可注入的策略", "说明 fixture 对资源作用域和清理的替代价值"],
            explain="""### 意图：固定流程骨架，让子类补不同步骤
每个接口用例都要准备数据、请求接口、断言结果、释放数据。有的同学把清理写在断言后面，测试一失败数据就留在环境里。这里应该固定的是步骤和资源回收规则，不同的是如何准备数据、请求什么、断言什么。基类提供唯一入口，子类只覆盖约定的步骤。

### 最小例子：失败后也会走清理
```python
class Case:
    def execute(self):
        try:
            self.setup()
            self.check(self.run())
        finally:
            self.teardown()

class SearchCase(Case):
    def __init__(self):
        self.rows = []

    def setup(self):
        self.rows.append("gym")

    def run(self):
        return list(self.rows)

    def check(self, actual):
        assert "station" in actual

    def teardown(self):
        self.rows.clear()

case = SearchCase()
try:
    case.execute()
except AssertionError:
    assert not case.rows
else:
    raise AssertionError("应产生断言失败")
```
`check` 是断言步骤，用与语法关键字不同的名字；`execute` 才是模板方法。因为示例把 `setup` 放在 `try` 内，清理必须能处理“资源只建了一部分”的情况；真实实现可每创建一项就登记回收，按逆序清理，或把资源封进上下文管理器。还要记录清理失败，避免清理抛错把主错误变成报告里的次要信息；示例只清空内存列表，不涉及失败流程合并。

### 取舍与面试话术
模板方法靠继承形成约定，子类最好别覆写 `execute`；不受控制地添加 hook 会让一个固定骨架变成一套难追踪的隐式规则。策略则用参数传入行为，可以在同一用例实例上替换某个步骤，而非必须派生另一个子类。责任链允许节点不再向下传，这里的测试生命周期不允许跳过回收。面试可以说：“我用基类保持固定流程，项目复杂后优先用 fixture 做可组合的资源管理，把业务断言留在用例里；验收看失败是否清理、清理错误是否可定位。”""",
            followups=[dict(q="setup 失败后，teardown 一定有东西清吗？", a="不一定，因此从空状态起步，资源真正创建后才记录标识和清理动作。用例可能只成功建了前半段资源，清理要处理空状态并可安全重入。"), dict(q="框架已经有 fixture，还需要基类吗？", a="多数时候不用重复造生命周期；用 fixture 管数据、连接与释放，用普通函数写执行和断言。需要明确复用一段团队自定义流程时再决定基类还是普通组合函数。")],
            pitfalls=["子类改骨架入口绕过清理约定", "把释放资源只写在断言后的成功路径"],
            hook="用最小样例分别让准备、请求、断言失败，再加一条清理失败的用例。报告应保留失败发生的阶段，测试资源或账号最终能归还，重复运行之间不受脏数据影响。",
        ),
        dict(
            id="pattern-chain",
            q="责任链模式是什么？请求中间件为什么适合用它？",
            level=2,
            short="责任链把多个处理者接起来，让请求按顺序过节点；节点可处理后直接返回、传给下一个，或先做检查再继续。比如客户端测试平台入口先检查身份、再检查配额，任一失败就截断，从而不打下游。策略通常选一个算法，观察者通常通知多方；责任链关心顺序和谁可以终止传播。",
            points=["说出处理者同一契约与依次传递请求", "节点根据条件处理、继续或短路", "说明顺序、链尾默认行为和短路可观测性", "用身份检查、配额过滤或审批流举例", "比较固定模板、单策略选择、多订阅者通知"],
            explain="""### 意图：把一串有顺序的处理规则拆成独立节点
请求进测试平台时，要先知道调用主体，再检查它的配额，最后才提交任务。如果把规则全部塞进入口函数，顺序与失败行为不好单独验证。责任链让每个节点只看自己负责的条件；靠约定决定是传给后继，还是就此结束。经典做法可以是第一个能处理者接管；中间件场景也常见多个节点各处理一段再继续。

### 最小例子：任一节点可短路
```python
visited = []

def identity(request):
    visited.append("identity")
    if not request.get("principal"):
        return 401, "missing identity"
    return None

def quota(request):
    visited.append("quota")
    if request["remaining"] <= 0:
        return 429, "quota exhausted"
    return None

def handle(request, checks):
    for check in checks:
        result = check(request)
        if result is not None:
            return result
    visited.append("submit")
    return 202, "queued"

assert handle({"remaining": 0}, [identity, quota])[0] == 401
assert visited == ["identity"]
visited.clear()
assert handle({"principal": "tester", "remaining": 2}, [identity, quota])[0] == 202
assert visited == ["identity", "quota", "submit"]
```
列表表达顺序，`None` 约定为放行，最终提交是默认行为。这只是对已解析上下文的流程示意，不是实际认证或限流实现。真实中间件也可把 `next_handler` 交给节点，让它在后继返回时补耗时或日志。审批也能这么建：节点按额度决定自己是否能审批，否则交给更高层；没人接管时应明确拒绝或转人工，不能默认为成功。

### 取舍与面试话术
链条易插拔，但顺序是业务契约。记录短路节点、理由和请求关联标识，排查时才能知道任务为什么没进到队列。如果前一节点负责填充上下文，后一节点就不能无条件放到前面；启动时验证配置，避免安全关键节点被漏装。答题时给一条成功轨迹与一条被截断轨迹：策略只选一套规则来做；模板方法由骨架掌舵，节点不随意终止清理；观察者没有同样的处理接力语义。""",
            followups=[dict(q="节点顺序调换是否一定无影响？", a="不一定。配额规则可能需要已确认的主体，前置检查失败还影响返回码优先级。把这种依赖写到配置验证和集成用例里，并测试多项条件同时不满足时的结果。"), dict(q="链上中间件怎么记录完整耗时？", a="可把后继包装为可调用对象，中间件在调用前开始计时，finally 记录耗时。若请求未到后继也要标出短路原因；注意区分节点自身和整个下游耗时。")],
            pitfalls=["遗漏链尾无人处理时的默认行为", "只断言状态码，不断言短路时下游没有副作用"],
            hook="写三组链路测试：全放行、首节点拒绝、中间节点拒绝。除了状态与原因，检查后续节点调用轨迹和任务队列是否新增记录；另测必要过滤器没配置时启动失败。",
        ),
        dict(
            id="pattern-adapter",
            q="适配器模式解决什么问题？和装饰器、代理怎么区分？",
            level=3,
            short="适配器把一个现有对象的接口和语义翻译成调用方已经期待的接口，让原来不兼容的两个部分能合作。例如报告层只认毫秒和统一状态，旧执行器返回秒和历史状态名，就在边界用适配器做转换。装饰器保留接口来叠能力，代理保留接口来管理访问，适配器则是为了兼容不同接口。",
            points=["说出对接不兼容接口的意图", "用组合持有旧对象，显式转换方法和数据", "覆盖单位、状态与错误映射，未知值不静默成功", "按换接口、叠能力、管访问区分三者", "说明统一契约的等价性验证"],
            explain="""### 意图：让不兼容的两个部分能用现有契约合作
测试平台升级结果存储，但旧任务执行器还在使用。新报告层期待 `result()` 给出毫秒与统一状态，旧执行器只提供 `outcome()`，单位是秒，状态也另有一套。直接改旧执行器可能影响老任务；在边界放适配器，可让新报告和老任务分别按原契约工作。这个模式真正费力的是语义翻译，而非换方法名。

### 最小例子：翻译执行结果而不是重写执行器
```python
class LegacyRunner:
    def outcome(self):
        return {"status": "ok", "seconds": 0.25}

class ResultAdapter:
    STATUS = {"ok": "passed", "bad": "failed"}

    def __init__(self, legacy):
        self.legacy = legacy

    def result(self):
        record = self.legacy.outcome()
        status = self.STATUS.get(record["status"])
        if status is None:
            raise ValueError("未知的旧系统状态")
        return {"status": status, "duration_ms": round(record["seconds"] * 1000)}

def summarize(reader):
    result = reader.result()
    return f'{result["status"]} in {result["duration_ms"]} ms'

assert summarize(ResultAdapter(LegacyRunner())) == "passed in 250 ms"
```
调用方只认识新接口，也可以拿一个原生实现替换适配器。例子约定取整到毫秒；实际项目需要明确舍入和精度，统一缺失值、取消状态与异常类型。没法保真的语义应显式暴露，不要把未知状态映射成通过，也不要擅自去补发任务。通过组合持有旧对象，适配层不需要继承外部类，可以在测试里注入最小替身。

### 取舍与面试话术
工厂可能负责选“新实现还是适配后的旧实现”，但选完之后是适配器承担翻译。装饰器不要求两边接口不同，通常仍能把内外对象给同一个调用点使用；代理则把访问入口放在对象外侧。面试按“调用方的契约 → 旧方差异 → 转换与不可转换 → 如何验收”说：同一报告测试同时跑原生实现和旧适配实现，结果单位与失败语义必须一致。适配器应尽量薄；逻辑越堆越多时需要明确是契约兼容，还是业务本身在演进。""",
            followups=[dict(q="旧接口只有成功和失败，但新接口还有取消怎么办？", a="不能从不存在的信息推导取消；先引入补充状态来源，或在新契约中显式标记未知并告警。如果下游必须判断取消，就需要调整上游协议，而非硬做一对一映射。"), dict(q="同时有新旧两套实现，怎么减少重复验证？", a="抽出共享契约用例覆盖状态、单位、缺失值和异常，然后参数化注入两种实现；在适配器自身再测历史别名、舍入边界和未知字段的处理。")],
            pitfalls=["只改方法名，不转换单位或异常含义", "把不认识的旧状态默默当成功"],
            hook="接入不同执行器时保留一组脱敏的历史结果样本，验证适配前后统计口径一致。对取消、超时、零耗时与未知状态都留例子，预防报告把失败漏掉或把秒按毫秒显示。",
        ),
        dict(
            id="pattern-builder",
            q="建造者模式为什么适合造测试数据？和工厂怎么选？",
            level=3,
            short="建造者把复杂对象的组装过程拆成可读步骤，在 `build()` 时统一校验并生成结果。测试里先提供一套有效默认值，再用链式方法突出本例关心的字段，比如库存、价格和可售状态。工厂着重选哪种对象或给预设成品，Builder 着重同一个对象怎么组装；字段少时直接用构造参数更简单。",
            points=["把复杂对象创建拆成多步并在 build 校验", "测试数据用有效默认值和显式业务覆盖", "产物与 Builder 状态隔离，新的用例用独立 Builder", "区分直接创建、数据工厂预设和分步组装", "对非法输入测试明确绕开有效 Builder"],
            explain="""### 意图：把复杂组装与最终对象表示分开
假设造一件商品要填名称、库存、价格、可售状态。每条用例全写一遍，评审看不出到底测什么；而一串位置参数又很容易填错。建造者为常规场景提供有效起点，再通过命名步骤修改本例关注的值，最后统一校验跨字段规则。经典思路也可让相同的组装流程交给不同 Builder，得到不同表示；测试数据里常用较轻的链式写法。

### 最小例子：默认有效，构建时验证约束
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Product:
    name: str
    stock: int
    available: bool

class ProductBuilder:
    def __init__(self):
        self.values = {"name": "demo", "stock": 10, "available": True}

    def with_stock(self, stock):
        self.values["stock"] = stock
        return self

    def unavailable(self):
        self.values["available"] = False
        return self

    def build(self):
        if self.values["stock"] < 0:
            raise ValueError("库存不能为负")
        if self.values["available"] and self.values["stock"] == 0:
            raise ValueError("此测试模型要求可售商品有库存")
        return Product(**self.values)

builder = ProductBuilder()
normal = builder.build()
sold_out = builder.with_stock(0).unavailable().build()
assert (normal.stock, normal.available) == (10, True)
assert (sold_out.stock, sold_out.available) == (0, False)
```
示例规则只属于假想业务，不代表真实电商都不允许可售状态下库存为零。已建好的产物只含不可变值，之后改 Builder 不会改变它；嵌套列表或字典要另外复制或转成不可变结构。用例之间不要共享可变 Builder。测非法库存时直接构造非法 HTTP 入参，否则 Builder 先拒绝了数据，根本没覆盖服务端的校验。

### 取舍与面试话术
简单数据用带关键字的构造参数，字段多但只要一个固定预设用数据工厂；多个可选步骤、跨字段约束和复用需求都出现时用 Builder。工厂也可返回预设 Builder，两者不是互斥。末尾把组装和落库分开：`build()` 只产出对象，显式调用 test fixture 才写数据，方便回收。面试重点是让用例读起来像业务规则，而不是展示链式调用本身。""",
            followups=[dict(q="测试数据默认值越多越好吗？", a="默认值应少而稳定，只覆盖与用例无关的合法字段；会影响断言的业务变量必须显式设置。例如测库存时明确写出数量，不能依赖别人随时能改的默认值。"), dict(q="Builder 建出的对象如何落库再回收？", a="保持构建纯内存，把持久化交给 fixture 或专门的数据客户端；成功落库就记录资源 ID 与所属命名空间，结束后精确删除并检查残留，避免跨用例误删。")],
            pitfalls=["测试非法输入时让 Builder 先拒绝，没触达到服务端", "把一个可变 Builder 当作所有并发用例共用的全局对象"],
            hook="为测试数据层做契约测试：默认对象合法、显式字段覆盖有效、两个构造对象互不影响、非法组合能报出原因。再为落库 fixture 验证唯一标识和失败后的清理。",
        ),
        dict(
            id="pattern-solid",
            q="SOLID 五条设计原则分别是什么？能说说反例吗？",
            level=2,
            short="单一职责是把不同变化原因拆开，开闭原则是让常见变化靠扩展而非改稳定核心，里氏替换是子类型不破坏父契约，接口隔离是不强迫调用方依赖用不着的方法，依赖倒置是让高层规则和低层细节都依赖抽象。比如测试执行器只依赖一个报告出口，不直接绑定某种存储，并用契约测试约束所有实现。",
            points=["SRP：单一变化原因，给出执行器同时改报告的反例", "OCP：针对可预期变化用扩展说明条件分支反例", "LSP：替换不破坏行为契约，说明返回值或异常反例", "ISP：调用方只依赖所需接口，举例过胖接口", "DIP：高层规则和低层实现依赖抽象，区分依赖注入手段"],
            explain="""### 为什么需要原则，而不是背英文字母
一个测试执行器同时跑用例、渲染报告、把报告写数据库。存储故障让结果丢失，改报告格式又要重测执行核心。SOLID 是用来诊断这个边界是否清楚的原则，不是五种模式，也不要求把所有代码拆成五层。

### 五条各用一句话，加一个反例
| 原则 | 意图 | 测试平台里的反例 |
|---|---|---|
| S 单一职责 | 让模块聚焦于同一类变化原因 | 执行器同时维护断言规则、报告页面和存储策略，每种需求都来改它。 |
| O 开闭 | 为已知变化留扩展点，尽量不改稳定流程 | 每增加一种通知渠道都复制并改一份运行逻辑。 |
| L 里氏替换 | 子类型应该保持调用方所依赖的行为契约 | 假存储实现承诺写入后可读，却只回成功、实际不保存，替换后测试预期失效。 |
| I 接口隔离 | 让客户端只依赖自己需要的接口 | 只读报告的组件却要依赖含删除、上传、重试的方法集合。 |
| D 依赖倒置 | 高层策略和低层细节都依赖抽象 | 执行器直接新建具体存储连接，单测没法无副作用地替换它。 |

### 最小例子：用小契约转移依赖方向
```python
from typing import Protocol

class ReportSink(Protocol):
    def publish(self, status: str) -> None: ...

def execute(check, sink: ReportSink):
    status = "passed" if check() else "failed"
    sink.publish(status)
    return status

class MemorySink:
    def __init__(self):
        self.items = []

    def publish(self, status):
        self.items.append(status)

sink = MemorySink()
assert execute(lambda: False, sink) == "failed"
assert sink.items == ["failed"]
```
执行器面对的是小协议；内存实现与其他实现都遵守 `publish`。注入实现是技术手段，依赖倒置是边界的方向；即使通过参数传入某个具体存储并调用它独有的方法，也不自然满足依赖倒置。协议能描述签名，却不能自动证明语义：例如写入失败应报错还是缓存，必须约定并拿契约测试验证。

### 面试怎么说
先说每条原则给哪种变化留空间，再拿报告出口串起来说明隔离。开闭不是“核心永远不能改”；业务规则本身变了就该改，别为了死守扩展点而隐藏真实变化。只有一个很小的选择点，可以先传函数；既适用原则，又省掉多余接口。""",
            followups=[dict(q="单一职责是不是一个类只能有一个方法？", a="不是。判断标准是变化原因而非方法数量；执行器包含运行与阶段调度仍可围绕同一职责，报告格式却有另一条变化轴，适合解耦。"), dict(q="类型检查通过能证明里氏替换吗？", a="不能。方法签名一致只是一部分；还要检查前置条件、结果和异常约定，例如替换后不能突然要求调用方必须多传一个未约定的 ID。")],
            pitfalls=["把开闭解释成不允许改现有源码", "通过参数接收具体实现，就宣称已完成依赖倒置"],
            hook="拿一个最常改的测试组件画依赖图，区分业务判断、数据访问和报告输出。对外部边界定义小契约，并让真实实现与替身都跑同样的关键语义测试。",
        ),
        dict(
            id="pattern-test-framework",
            q="测试框架里 Page Object、数据工厂和数据驱动怎么用？",
            alt=["设计 UI 自动化框架时，页面、测试数据和关键字怎么分层？"],
            level=2,
            short="我让用例表达场景和预期，Page Object 封装选择器、等待与页面操作；数据工厂提供预设有效数据，Builder 让复杂数据按需覆盖。数据驱动是同一流程换输入和预期，关键字驱动是把动作名与参数编成不同流程，底层映射到页面或接口方法。取舍是先让代码用例清晰，再为确实有复用需求的场景引入关键字层。",
            points=["Page Object 包装页面操作和定位，与业务断言分离", "工厂提供有效默认值，Builder 显式叠加业务变量", "数据驱动同流程换一组输入输出", "关键字驱动按动作名和参数编排流程并校验关键字", "说明维护成本，按稳定边界选分层"],
            explain="""### 三条变化轴分开处理
登录页面经常改选择器，账户数据要按角色生成，用例还得覆盖合法与非法输入。把定位、流程、数据都写在一个脚本里，一次页面改版会让几十个脚本同时修。Page Object 给页面行为起业务名并封装定位、等待与动作；数据工厂管预设账户；用例负责看哪个结果是正确的。页面层可以验证页面是否就绪，涉及业务规则的断言仍留给用例。

### 一个可运行的最小例子
```python
class FakeDriver:
    def submit(self, selector, user):
        assert selector == "#login-submit"
        return "home" if user["enabled"] else "blocked"

class LoginPage:
    def __init__(self, driver):
        self.driver = driver

    def login_as(self, user):
        return self.driver.submit("#login-submit", user)

def user_factory(enabled=True):
    return {"name": "tester", "enabled": enabled}

page = LoginPage(FakeDriver())
for enabled, expected in [(True, "home"), (False, "blocked")]:
    assert page.login_as(user_factory(enabled)) == expected

actions = {"login": page.login_as}
steps = [("login", user_factory(False))]
assert [actions[name](value) for name, value in steps] == ["blocked"]
```
前一段同一个登录动作换数据、预期，是数据驱动。后一段外层流程按关键字分发，实际可列“打开登录页 → 登录 → 搜索 → 断言”，不同脚本的动作顺序也能变。例子用替身演示分层，不模拟真实浏览器的异步行为；生产用例应集中维护可靠定位与可观测的等待条件，例如结果区域出现，而不是处处固定睡眠。复杂账户组合再用 Builder，把本例在意的租户、角色、状态写出来。

### 取舍与面试话术
Page Object 不是“一个页面必须对应一个大类”，可把复用组件拆出去。数据驱动不是把每条差异用例都做成一张难读的表；特殊流程仍可单写。关键字层要校验未知动作、参数类型，报告显示原步骤、输入摘要和失败原因，否则调试要穿过用例表、解释器和页面对象三层。面试说“界面改只动页面层，数据扩只加行，流程复用才加关键字”，最后用改一个定位或新增一类账号的成本验证分层。""",
            followups=[dict(q="Page Object 和普通脚本最大的区别？", a="用例只表达诸如搜索地点、确认订单的业务动作，定位和页面就绪条件藏在 Page Object 里；普通脚本常把这些细节重复铺在每条用例中。"), dict(q="什么情况下不采用关键字驱动？", a="用例由开发团队直接维护、分支类型多且变化快时，直接写可调试的代码通常更合适。若新增关键字大量只调用一次，说明额外的语言层还未带来足够复用。")],
            pitfalls=["让 Page Object 变成同时读数据、跑业务断言和发报告的上帝类", "为追求零代码引入难调试且缺少校验的关键字表"],
            hook="选一组稳定冒烟用例试做分层：统计页面改动后需要修改的文件与失败定位耗时，验证页面对象行为、数据生成和关键字分发各自可单测，再决定扩到全量。",
        ),
    ],
)
