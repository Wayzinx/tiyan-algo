CHAPTER = dict(
    id="py", order=8, name="Python 语言特性",
    blurb="从对象引用和语言惯用法，到能独立写出可靠的测试",
    map="""| 板块 | 必会问题 | 一句话答案 |
|---|---|---|
| 对象与别名 | 参数传递、可变性、拷贝、is 有什么关系？ | 名字绑定对象；原地修改会被别名看到，重新绑定不会，拷贝决定共享到哪一层。 |
| 容器 | list、dict、set 怎么选？ | 按位置和顺序用动态数组；按键查找或去重用哈希表。 |
| 函数 | 装饰器为什么能包装函数，默认值为何串用？ | 函数可传递、闭包捕获绑定；默认值则在定义时求值一次。 |
| 数据流与资源 | yield、with 和垃圾回收分别负责什么？ | 生成器按需生产；with 确定性清理资源；回收器处理失去可达性的内存。 |
| API 契约 | 参数、类与异常怎么写得清楚？ | 用签名表达调用约束，用对象协议表达能力，只捕获知道如何处理的异常。 |
| 异步 | gather 怎么组织多个等待？ | 在事件循环里推进可挂起的操作，结果顺序与完成顺序不是一回事。 |
| 测开 | pytest 如何管理依赖、数据和外部调用？ | fixture 管装配与清理，parametrize 展开用例，patch 替换被测代码实际查找的名字。 |

**复习顺序**：先预测每个短程序的输出，再动手跑。第一遍练对象引用、容器、装饰器和生成器，第二遍练类、资源与异常，最后把 fixture、参数化和 mock 写进同一个用例。遇到“看起来一样”的代码，追问对象是不是同一份、求值发生在何时、失败由谁收尾。
""",
    cards=[
        dict(
            id="py-object-references",
            q="Python 的参数是按值传还是按引用传？可变类型有什么区别？",
            level=1,
            short="调用时，形参绑定到实参所指的同一个对象，也叫对象共享传递。重新给形参赋值只换了局部名字，不会把调用方的变量改绑；但如果通过这个名字原地修改列表、字典等可变对象，所有引用它的地方都能看到。整数、字符串和元组自身不可变，但元组里的可变元素仍可能被修改。",
            points=[
                "说明调用时形参和实参引用同一个对象，不会自动复制对象",
                "区分重新绑定局部名字与原地修改共享对象",
                "能举 list、dict 为可变，int、str、tuple 为不可变的例子",
                "指出 tuple 的元素引用固定，不代表内层对象不可变",
                "知道 += 可能原地更新也可能重新绑定，取决于对象类型",
            ],
            explain="""### 名字是标签，不是装对象的盒子
把变量想成贴在对象上的标签。`alias = batch` 不会生成第二个列表，只是两张标签贴到同一个列表上。调用函数时形参也拿到一张标签；改标签指向不会动到其他标签，但顺着标签去修改对象，两处都能观察到。这个模型叫对象共享传递，比只背“传引用”准确：不像一些语言的引用形参，Python 函数不能通过把参数重新赋值就改变调用者变量的绑定。

### 先预测这段代码的结果
```python
def update(batch, version):
    batch.append("retry")
    batch = ["discard"]
    version += 1
    return batch, version

jobs, current = ["first"], 1
returned_jobs, returned_version = update(jobs, current)
assert jobs == ["first", "retry"]
assert current == 1
assert (returned_jobs, returned_version) == (["discard"], 2)
```

`append` 修改原列表；下一行 `batch = ...` 只是把形参绑到新列表。整数无法原地变成 2，`version += 1` 的效果是让局部名字引用计算结果。换成列表的 `+=` 则一般原地扩展；面试时别把两种 `+=` 都当作 `x = x + y`，也别靠写法猜自定义类型会怎么实现。有别名时，选择不同写法会影响原调用者看到的内容。

### 不可变到底是哪一层不可变
字符串、整数不能原地改值；元组的每个位置指向哪个对象也不能改。但 `bundle = ([1],)` 中修改 `bundle[0]` 里的列表依然可行，因为改变的是列表内容，不是元组槽位。如果一个 API 承诺“不会改调用者的输入”，得说明是只不修改外层，还是连内层对象也不能动；复制外层不是深层隔离。

### 面试怎么说
先说“绑定同一个对象”，再举列表追加和形参重新赋值各一个例子。写业务代码时，若接口会原地修改输入，就让命名和文档说清楚；否则优先返回结果，不让调用者靠观察副作用猜发生了什么。""",
            followups=[
                dict(q="元组能当字典键，是不是所有元组都行？", a="不是。元组需要元素也可哈希；包含列表的元组虽不能替换元素引用，但该列表不可哈希，因此整个元组也不能直接用作字典键。"),
                dict(q="a 和 b 引用同一个列表，a += [1] 后 b 看到什么？", a="内置列表的原地加法扩展原列表，b 会看到新增元素。若写成 a = a + [1]，则创建新列表并重绑 a，b 仍引用旧的列表。"),
            ],
            pitfalls=["说函数调用会复制对象，或者说函数能直接改掉外部变量的绑定。", "把不可变容器误解为它引用的所有对象都不可变。"],
            hook="测开视角：排查某个参数化用例把公共数据改脏时，记录对象身份、修改前后快照和初始化来源。为处理函数写一条输入不被修改的断言，同时覆盖内层列表而不是只比较外层容器。",
            mnemonic="赋值换标签，原地改对象；改哪一层，观察哪一层。",
        ),
        dict(
            id="py-copy-depth",
            q="Python 的浅拷贝和深拷贝有什么区别，嵌套列表会怎样？",
            level=1,
            short="对嵌套列表，浅拷贝新建外层，内层仍是同一批引用；深拷贝递归复制需要复制的子对象，用 memo 记录已经处理的对象，既能应对循环，也能保留同一次拷贝内部的共享关系。只想加删外层元素，浅拷贝够用；要独立改嵌套测试数据时，再按需深拷贝或重建。",
            points=[
                "区别赋值、copy.copy 和 copy.deepcopy 对外层及内层的影响",
                "能预测浅拷贝时内层列表修改会反映到原对象",
                "理解 deepcopy 利用 memo 处理循环引用并保留原有共享结构",
                "深拷贝不保证每个对象都换身份，连接或文件等资源不宜直接复制",
            ],
            explain="""### 外层复制和整棵结构隔离是两件事
测试平台有一组模板，每个模板里还有多步操作。你为每个用例复制模板数组，随后只改其中一个步骤，却发现下个用例也受影响。原因不是 `copy` 没执行，而是浅拷贝只复制了数组外壳，里面装的仍是指向原步骤的引用。赋值连外壳都不复制；深拷贝则按对象的拷贝规则递归处理内部结构。

### 一眼能看见的嵌套列表差异
```python
from copy import copy, deepcopy

row = [1]
original = [row, row]
alias = original
shallow = copy(original)
deep = deepcopy(original)

assert alias is original and shallow is not original
shallow.append([9])
shallow[0].append(2)
assert original == [[1, 2], [1, 2]]
assert deep == [[1], [1]] and deep[0] is deep[1]
assert deep[0] is not row
```

外层 `append` 没污染原列表，内层 `append` 同时改变原列表所指的那行。深拷贝时，两条路径都指向同一原行，只需要复制一份新行，两个位置继续共享它。`deepcopy` 用 `memo` 记录身份到拷贝的对应关系，因此像列表包含自身这样的循环结构也不需要无限递归。注意“隔离原对象”不等于“把每条路径都变成独立对象”。

### 什么时候别用深拷贝
只需要在外层排序、追加或删除时，用列表切片或浅拷贝就够。只改被测请求中的一个字段，也可以重建该字段及其外层对象，代码更能表达意图。复制整棵可达结构会增加时间和内存，并且函数等对象通常原样返回，打开的文件或连接并不是能可靠复制的运行时资源。测试夹具更适合从小的输入工厂重新构造这些资源，并显式清理。

### 面试怎么说
先说哪层是新对象，然后直接举外层加一行、内层加一个数字的对照；补一句 memo 保留共享关系。选择方案要对齐隔离要求，而不是默认深拷贝越多越安全。""",
            followups=[
                dict(q="列表切片为什么也会遇到这个问题？", a="切片为外层列表分配新的容器，但拷进去的仍是元素引用。替换一个位置不影响旧外层，修改那个位置原来引用的内层对象则仍会共享。"),
                dict(q="测试隔离总用 deepcopy 有什么问题？", a="它可能多复制大量不相关数据，也无法给连接或文件提供独立的有效副本。优先用工厂创建本次真正需要的对象，并且显式管理运行时资源。"),
            ],
            pitfalls=["看到两个外层对象的身份不同，就断定它们没有共享内部状态。", "认为 deepcopy 会为每个重复引用各复制一份互不相关的对象。"],
            hook="测开视角：对数据工厂做独立性测试，从同一模板生成两个请求，改第一个的嵌套列表或字典，再断言第二个和原模板都未变化。对于本来就要共享的只读配置，也显式记录约定。",
            mnemonic="赋值同壳，浅拷新壳，深拷换内层但保留共享结构。",
        ),
        dict(
            id="py-containers",
            q="list、dict、set 底层是什么，常见操作的复杂度是多少？",
            level=1,
            short="CPython 的 list 是存对象引用的动态数组，随机索引 O(1)，尾部 append 摊还 O(1)，中间插删和成员扫描 O(n)。dict 和 set 用哈希表，键查找、成员判断和常见增删平均 O(1)，最坏可能 O(n)。要保序和索引用 list，按键查值用 dict，只判断是否出现或做去重用 set。",
            points=[
                "说明 list 是动态数组而不是链表，索引 O(1)、尾插摊还 O(1)",
                "说明 list 中间插删需要移动元素，成员查找通常 O(n)",
                "说明 dict、set 基于哈希表，键和成员查找平均 O(1)，不是最坏保证",
                "知道 dict 保留插入顺序，而 set 的迭代顺序不应当成契约",
                "选型考虑可哈希条件、构建成本、附加内存和查找频率",
            ],
            explain="""### 为什么下标快不代表搜索快
列表像一排连续的格子，每格放的是对象引用。知道下标就能跳到对应格子；只知道值时，得挨个比较。CPython 列表扩容通常预留额外空间，所以多数尾插不用搬迁，算很多次追加的平均成本是摊还 O(1)，不代表单次扩容也恒定。头部或中间插删可能移动后续引用，通常是 O(n)。

### 哈希表用空间换查找速度
字典和集合用哈希帮助定位槽位，有冲突时还需继续寻找和比较；通常查找、增删成本是平均 O(1)，极端碰撞下可退化。这里默认单次哈希和相等比较成本有界，用户自定义键若计算很贵不能忽略。字典用可哈希的键找值，保证迭代体现插入顺序；集合只关心成员，不承诺按插入顺序迭代。列表本身不可哈希，不能直接当集合成员或字典键。

### 一个测试结果核对的例子
```python
submitted = ["case-3", "case-1", "case-3", "case-2"]
finished = {"case-1", "case-2"}
ordered_unique = list(dict.fromkeys(submitted))
missing = [case_id for case_id in ordered_unique if case_id not in finished]

assert submitted[0] == "case-3"
assert ordered_unique == ["case-3", "case-1", "case-2"]
assert missing == ["case-3"]
```

用 `dict.fromkeys` 去重还保留首次出现顺序；用 `set` 做完成状态的成员判断。如果完成结果本来是长度为 m 的列表，待验证项有 n 个，每项线性扫描最坏需要 O(nm) 次比较。先建集合通常要 O(m) 时间与空间，再逐个查找通常共 O(n)，查询次数多时值得；只查一次小列表就没必要先构建集合。

### 面试怎么说
对着操作回答复杂度：按位置、按值、按键不是一回事。最后补一句平均、摊还和最坏的区别，然后用重复查找换哈希索引的例子解释为什么选这个容器。""",
            followups=[
                dict(q="为什么列表不能直接放进集合？", a="列表可变且标准实现不可哈希；哈希键必须在其作为键期间保持可用的哈希和相等语义。可以按业务改用元素都可哈希的元组或其他稳定键。"),
                dict(q="用 list 做 FIFO 队列为什么越来越慢？", a="pop(0) 删除首项后要移动后面的引用，随长度增长。大量两端操作可用 collections.deque；如果还需要多线程阻塞和完成通知，考虑 queue.Queue。"),
            ],
            pitfalls=["说 list 的 in 能按下标直接定位，所以是 O(1)。", "把字典与集合的 O(1) 当作无条件的最坏耗时上界。"],
            hook="测开视角：写对账脚本时往往会对每个预期 ID 反复查结果，先用哈希索引避免嵌套扫描。用线上量级的脱敏形状或合成数据验证耗时和内存，并单独断言展示顺序、缺失项和重复项。",
            mnemonic="下标用数组，查键用字典，只问有没有用集合。",
        ),
        dict(
            id="py-decorators",
            q="Python 装饰器是什么，怎么写带参数的计时装饰器？",
            level=1,
            short="函数在 Python 里可以当参数、返回值和变量。装饰器接收函数并返回替代对象，常用闭包记住原函数和配置；@decorator 相当于定义后把名字重新绑定到 decorator(func)。带参数时外层先收配置并返回真正的装饰器，包装函数用 *args、**kwargs 转发，并用 functools.wraps 保存元数据。",
            points=[
                "用函数是一等对象和闭包解释包装器如何保留原函数",
                "写出普通装饰与带参数装饰的等价重新绑定表达式",
                "区分定义时形成包装与调用时执行包装逻辑",
                "用 functools.wraps 保留元数据并提供 __wrapped__",
                "转发位置和关键字参数，保留返回值及异常语义",
            ],
            explain="""### 为什么不在每个函数里重复写计时
要给十个测试工具函数加耗时记录，若每个函数头尾都写计时，很容易漏掉异常路径。函数作为一等对象，可以传给一个负责加外壳的函数；外壳通过闭包记住原函数，调用时先计时、再委托给原函数、最后记录。`@decorate` 放在定义上方，和定义后执行 `func = decorate(func)` 是同一种绑定效果。带参数的 `@timed(records)` 则先调用工厂拿到装饰器，再用它包装原函数。

### 从外到内写三层
```python
from functools import wraps
from time import perf_counter

def timed(records):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            started = perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                records.append((func.__name__, perf_counter() - started))
        return wrapper
    return decorate

records = []

@timed(records)
def add(left, *, right):
    return left + right

assert add(2, right=3) == 5
assert add.__name__ == records[0][0] == "add"
assert records[0][1] >= 0
```

外层收记录容器，中层收原函数，内层才收每次调用的实参。计时用 `perf_counter` 的差值，不用日历时间；`finally` 负责异常时也记录，如果记录动作自身不失败，原异常照常传播。`wraps` 复制名称、文档等元数据并设置 `__wrapped__`，帮助调试和签名检查；它不是把包装函数的参数列表字面改成原签名。

### 别让包装偷偷改变业务契约
叠多层时，`@outer` 放在 `@inner` 上方等价于 `outer(inner(func))`。这个顺序会改变被观测范围：计时包在重试外面会覆盖整个重试过程，包在里面记录每次尝试。异步函数要用异步包装器 `await` 原函数才能测到执行耗时，用普通包装器只会测到返回协程对象的过程。处理参数、返回值、异常时都要尊重被装饰接口的约定。

### 面试怎么说
先写等价绑定，再从外到内说“收配置、收函数、收调用参数”。最后解释 wraps 和异常路径，这比只背语法更能说明自己写过。""",
            followups=[
                dict(q="怎么写一个不会误重试的重试装饰器？", a="只捕获明确可重试的异常，限制次数和总时限，加入适当退避，耗尽后传播失败。对有外部副作用的操作还要先保证幂等，否则重试可能重复提交。"),
                dict(q="为什么装饰器里调用原函数必须 return？", a="包装后的名字指向 wrapper；如果 wrapper 算出结果却不返回，调用者拿到的是 None。装饰器负责转发原返回值，除非它的契约明确要转换结果。"),
            ],
            pitfalls=["以为函数每次调用都会重跑装饰器工厂。", "包装时漏掉 return、kwargs 或 wraps，导致行为或调试信息变了。"],
            hook="测开视角：对计时包装器分别喂正常返回与主动抛异常的函数，断言原结果或异常保持不变，并且记录都产生。测耗时逻辑时替换包装器查找的时钟，别断言机器上某次实跑一定耗时多少。",
            mnemonic="配置一层、函数一层、调用一层；转发不丢，元数据用 wraps。",
        ),
        dict(
            id="py-generators",
            q="迭代器和生成器是什么关系，为什么适合读大文件？",
            level=1,
            short="迭代器按 next() 逐个给值，耗尽抛 StopIteration。生成器是实现迭代器的一种方式：调用带 yield 的函数得到生成器对象，第一次取值才开始执行，每次 yield 产出一个值并保存暂停位置。逐行筛选文件只保留当前行和少量状态，不需要把整个输入先装进列表。",
            points=[
                "区分可迭代对象、迭代器与生成器，解释 iter、next 和 StopIteration",
                "说明调用生成器函数不立即执行函数体，yield 保存现场后按需恢复",
                "给出逐行读取并边过滤边统计的大文件处理办法",
                "知道生成器单次消费、可能长期持有资源，list 会抵消流式优势",
            ],
            explain=r"""### for 循环到底问了什么
列表可迭代，是因为 `iter(列表)` 能得到一个带当前遍历位置的迭代器。`for` 先拿迭代器，再不断取 `next()`，遇到 `StopIteration` 正常停止。一个列表通常能重复创建新迭代器，但同一个用完的迭代器不会自动回到开头。生成器对象已经是迭代器：它把下一步实现成恢复一段暂停的函数代码。

### 从按需产出理解节省内存
```python
import sys
from io import StringIO

def failed_ids(lines):
    for line in lines:
        case_id, status = line.split()
        if status == "FAIL":
            yield case_id

if len(sys.argv) == 2:
    with open(sys.argv[1], encoding="utf-8") as lines:
        print(sum(1 for _ in failed_ids(lines)))
else:
    with StringIO("case-1 PASS\ncase-2 FAIL\ncase-3 FAIL\n") as sample:
        failures = failed_ids(sample)
        assert iter(failures) is failures
        assert next(failures) == "case-2"
        assert sum(1 for _ in failures) == 1
        assert next(failures, None) is None
```

脚本不带参数时用内存中的三行样例做断言，带日志路径时才从磁盘逐行读，每行格式是“用例号 状态”。调用 `failed_ids` 只建立生成器，第一个 `next()` 扫到首条失败时暂停；下一次才从那里接着走。磁盘分支只持有 I/O 缓冲、当前行附近的数据与常数规模的统计状态，不累积全部输入或结果；单行极大时仍要考虑峰值。

### 惰性不等于自动省资源
如果下游立刻 `list(failed_ids(lines))`，所有命中重新进入内存；如果函数把生成器返回给外面却先关闭它依赖的文件，消费时就可能读失败。要明确文件所有权，能在 `with` 内消费就别把流丢到外面。生成器适合一次遍历和早停；若业务要随机索引、小数据多次遍历或比较全量快照，列表反而简单。

### 面试怎么说
先说“生成器是一种迭代器，yield 暂停并按需恢复”，再用大日志逐行筛选、边读边聚合举例。最后点出不要一次读全文件或把全部结果收回列表。""",
            followups=[
                dict(q="生成器里的报错会在什么时候出现？", a="普通生成器函数的函数体在开始迭代后才执行，解析错误可能在某个 next 才抛出。因此测试不能只创建生成器就结束，要消费到目标数据位置。"),
                dict(q="yield 和 return 有什么不同？", a="yield 交出当前值而保留现场供后续恢复；生成器中的 return 结束遍历。普通 for 循环接收 yield 的值，不会把生成器的 return 值当作一个元素。"),
            ],
            pitfalls=["说生成器与迭代器互斥，或以为下一轮迭代会自动重放。", "上游改成生成器，下游却整体收集数据，仍声称峰值内存不随数据量增长。"],
            hook="测开视角：用内存文本流测空输入、格式错误与提前停止，再用大文件测内存峰值。解析错误要在消费阶段断言；对提前中止的任务，还要验证文件在约定的作用域退出时关闭。",
            mnemonic="iter 找入口，next 拿下一项，yield 暂停不是结束。",
        ),
        dict(
            id="py-identity-equality",
            q="is 和 == 有什么区别？为什么判断 None 要用 is？",
            level=2,
            short="is 判断是不是同一个对象，不走自定义相等逻辑；== 判断值是否相等，可由类型实现。None 是单例，判断是否正是它就用 is None。CPython 可能复用小整数对象，编译器也可能合并常量，所以两个数字偶然 is 为真不能作为业务逻辑；比较数字或字符串的值仍用 ==。",
            points=[
                "is 比较对象身份，== 比较相等语义并可能调用 __eq__",
                "用两个值相等但不共享身份的列表举例",
                "None 单例用 is None，不把 None 和其他假值混在一起",
                "小整数缓存、常量复用属于实现细节，不依赖具体边界",
            ],
            explain="""### 两份内容一样，不等于就是同一份
打印两个列表都是 `[1, 2]`，但你修改第一个，不一定会改变第二个。因为“内容一样”回答的是值的问题，“是同一份”回答的是身份的问题。相等比较能由类型用 `__eq__` 定义，例如某个业务对象判断相同 ID 就相等；身份比较不能被用户类重写，不取决于对象内部的字段。

### 用列表与哨兵验证区别
```python
first = [1, 2]
second = [1, 2]
alias = first
assert first == second and first is not second
assert first is alias

missing = object()
payload = {"score": 0, "comment": None}
assert payload.get("other", missing) is missing
assert payload.get("comment", missing) is None
assert payload["score"] == 0

left, right = int("42"), int("42")
assert left == right
print(left is right)
```

示例里缺少字段、字段明确为 `None`、字段为 `0` 是三种状态。用 `if not value` 会把后两种假值一起拦下；用独特的 `object()` 当默认哨兵，就能把“未给”与“明确给了一个空值”区分开。判断是否为 `None` 时，`is None` 不会触发可能被重载的 `==`，正好表达所需的语义。

### 为什么小整数实验看起来不一致
CPython 会缓存一部分常用小整数，不同表达式还可能在编译过程中复用常量。因此就算两个式子各写了一次数字，也不一定创建两个对象。同一段脚本、交互环境或不同实现的构造路径未必一样，示例只打印身份实验的结果，不把它写成断言。身份主要用在明确的单例、哨兵、别名判断上；比较数值、字符串或测试结果内容始终走类型的相等规则。

### 面试怎么说
一句话区分身份和值，再举列表、None 和整数缓存三个例子。不要给缓存范围背书，也不要用 `is` 检查两个业务字段恰好都等于 42。""",
            followups=[
                dict(q="id() 一样能永久证明同一个对象吗？", a="两个同时存活的对象具有不同的身份标识，比较存活对象可直接用 is；对象销毁后其 id 可能被重用，不要把历史 id 当成永久唯一主键。"),
                dict(q="None、空字符串和零为什么要分开测？", a="它们在布尔上下文都为假，但业务经常视为未填写、显式空值和合法的零分或零次。测试分别构造输入，确认代码按字段契约判断，而不是用通用真值合并。"),
            ],
            pitfalls=["在整数或字符串比较中使用 is，并根据一次交互实验得出结论。", "用 if not value 代替 is None，吞掉合法的空字符串或零。"],
            hook="测开视角：当接口允许空值时，把缺失、None、空串、零、False 分成显式参数组，并断言拒绝原因或保留的值。检验数据隔离时再用 is 判定两个调用有没有意外共享同一对象。",
            mnemonic="认人用 is，比内容用 ==，缺省值看哨兵。",
        ),
        dict(
            id="py-binding-traps",
            q="为什么默认列表会跨调用共享，循环里 lambda 为什么拿到最后一个值？",
            level=2,
            short="默认参数表达式在执行函数定义时求值一次，省略参数的调用会复用同一默认对象，所以别拿列表当默认值再修改。闭包通常捕获外部变量的绑定而非当时的值，循环里创建的 lambda 在后来执行时会读到循环变量最后绑定的值。可分别用 None 后新建对象、默认参数或工厂绑定当轮值来修复。",
            points=[
                "默认参数求值发生在函数定义时，不是每次调用时",
                "可变默认值导致省略参数的各次调用共享并累积状态",
                "用 None 或独特哨兵判断省略，再在函数体新建对象",
                "闭包延迟读取外部绑定，循环的多个函数可能读到同一最终值",
                "给出 lambda 默认参数或独立工厂作用域保存当轮绑定的修法",
            ],
            explain="""### 两个时间点：定义时和调用时
有些代码错误不是值算错，而是对“什么时候拿到那个值”理解错。函数默认值写在定义上，它在执行定义时算好，留给之后的调用复用。闭包里的普通自由变量则不是自动拍快照，而是在执行闭包时读当前绑定。一个算得比想象中早，一个读得比想象中晚。

### 让错误和修复一起跑
```python
def unsafe_add(value, items=[]):
    items.append(value)
    return items

def safe_add(value, items=None):
    if items is None:
        items = []
    items.append(value)
    return items

assert unsafe_add("first") == ["first"]
assert unsafe_add("second") == ["first", "second"]
assert safe_add("second") == ["second"]

def build_callbacks():
    late = [lambda: index for index in range(3)]
    bound = [lambda index=index: index for index in range(3)]
    return late, bound

late, bound = build_callbacks()
assert [callback() for callback in late] == [2, 2, 2]
assert [callback() for callback in bound] == [0, 1, 2]
```

`unsafe_add` 的三个调用者即使互不相识，也可能改同一份默认列表。`safe_add` 只在省略或传 None 时新建列表，显式传入的空列表仍按接口原地修改。闭包例子里，推导式每轮没有替自由变量建一套独立存储；所有延迟版回调执行时读到同一个最终值。绑定版利用“默认值在定义时求值”让每轮 `lambda` 保存自己的对象引用。如果对象是列表，后续原地改列表仍然可见；保存引用不等于深拷贝。

### 面试怎么说
先点出定义和调用的时间差，再分别给出一行修法。`None` 若是有意义的合法输入，就用独特哨兵区分是否省略；如果不希望外部能通过参数覆盖闭包里的值，使用工厂函数为每次创建独立的局部绑定。只有主动设计共享缓存时才考虑保留跨调用状态，且应显式表达生命周期。""",
            followups=[
                dict(q="为什么不用 items = items or []？", a="空列表是假值，这样写会把调用者主动传入的空列表替换掉，改变原地更新的契约。用 is None 或身份哨兵只处理约定的缺省输入。"),
                dict(q="闭包捕获变量会延长对象寿命吗？", a="闭包持有它所需的变量绑定，绑定所引用的对象可能在外层函数返回后仍存活。长期保存回调时，不要无意捕获整个重型测试上下文。"),
            ],
            pitfalls=["只测第一次调用，误以为带默认列表的函数没有共享状态。", "在循环中立即调用回调测得正常，没覆盖实际的延迟执行路径。"],
            hook="测开视角：数据工厂要连续调用至少两次并检查默认数据彼此独立。批量注册回调则应先全部注册、后按不同顺序触发，比较每个回调收到的用例标识，才能发现任务全部指向最后一项的回归。",
            mnemonic="默认值定义时算，闭包自由变量调用时取。",
        ),
        dict(
            id="py-context-managers",
            q="with 怎么工作的，如何自己写一个上下文管理器？",
            level=2,
            short="with 把申请和释放资源绑在同一个作用域里。进入时调用 __enter__，其返回值绑定给 as；成功进入后，不论正常还是异常离开，都会调用 __exit__。异常退出时如果它返回真值，异常被抑制，否则继续传播。也可以用 contextlib.contextmanager：yield 前申请，yield 交付资源，finally 清理。",
            points=[
                "说明 __enter__ 的返回值和 as 的关系，未必是管理器本身",
                "成功进入后调用 __exit__ 负责正常与异常路径清理",
                "异常传给 __exit__，返回真值会抑制该异常",
                "contextmanager 用单次 yield 分隔进入和退出阶段，用 finally 收尾",
            ],
            explain="""### 不给清理留一个“记得调用”的口子
文件、锁、临时设置需要成对申请和释放。如果只有正常分支写了关闭，抛异常、提前返回等路径容易漏掉。`with` 不是为了让代码短几行，而是让资源的生存范围从缩进上一眼看出来。成功进入后，正常结束、异常退出、提前返回都会执行退出协议；如果 `__enter__` 自己失败，`__exit__` 不会替它清理已部分申请的资源。

### 类和生成器各写一次
```python
from contextlib import contextmanager
from io import StringIO

class BufferSession:
    def __enter__(self):
        self.stream = StringIO()
        return self.stream

    def __exit__(self, exc_type, exc_value, traceback):
        self.stream.close()
        return False

@contextmanager
def temporary_setting(settings, name, value):
    previous = settings[name]
    settings[name] = value
    try:
        yield settings
    finally:
        settings[name] = previous

settings = {"mode": "normal"}
try:
    with BufferSession() as stream, temporary_setting(settings, "mode", "test"):
        assert settings["mode"] == "test"
        raise ValueError("simulate failure")
except ValueError:
    assert stream.closed and settings["mode"] == "normal"
else:
    raise AssertionError("failure must propagate")
```

类的 `as stream` 拿到的是缓冲区，不是 `BufferSession` 本身；异常类型、值和回溯会传给 `__exit__`，返回 False 让异常继续。生成器版在 `yield` 交出资源，体内异常会回到 `yield` 位置，因此 `finally` 仍会还原状态。多个上下文按嵌套理解，按进入的反顺序退出。示例的设置必须已有这个键，且是示范单线程作用域，不适合直接改并发测试的全局状态。

### 面试怎么说
先讲“进来拿，出去还”，然后说明会不会吞异常。短小、一次性的包裹逻辑适合 `contextmanager`，需要管理更多状态或行为时考虑类。不要把资源释放寄托在解释器什么时候回收对象上。""",
            followups=[
                dict(q="如果 __enter__ 已经打开一个资源，接着第二个打开失败怎么办？", a="当前管理器尚未成功进入，不能指望 __exit__ 被调用。应在 __enter__ 里自己回退，或使用 ExitStack 在每次申请成功后立即登记对应退出动作。"),
                dict(q="什么时候应该返回 True 吃掉异常？", a="只有明确的上下文契约允许时，例如某个预期且可恢复的异常。过滤指定异常类型，并测试意外异常仍向外传播；清理本身不等于处理失败。"),
            ],
            pitfalls=["误以为 __enter__ 抛异常后仍会调用该管理器的 __exit__。", "为了不报错让 __exit__ 一律返回 True，掩盖业务失败。"],
            hook="测开视角：资源夹具至少验证正常退出、业务抛异常、后续资源申请失败三条路径。用替身记录释放顺序和次数，确认临时配置、锁和读写句柄都恢复，不让一个失败污染后面的用例。",
            mnemonic="进入取资源，退出收资源；抑制异常必须有约定。",
        ),
        dict(
            id="py-garbage-collection",
            q="CPython 怎么回收对象，为什么要在引用计数之外处理循环引用？",
            level=2,
            short="CPython 3.12 主要靠引用计数：普通对象失去最后一个强引用后通常会立即回收；相互引用的对象即使外部已经够不到，内部计数仍可能不归零。循环收集器在候选对象中追踪可达性，把不可达环找出来清理，并做分代，年轻对象更常检查。文件等资源仍应主动关闭。",
            points=[
                "限定为 CPython 3.12 的引用计数和循环收集机制",
                "描述环内强引用使外部不可达对象的计数仍然不归零",
                "能用标记清除思路说明追踪候选可达性，而非把所有对象周期性全扫一遍",
                "说明 3.12 循环收集器三代，年轻对象通常更常被检查",
                "区分 del、对象回收、操作系统内存下降和显式资源释放",
            ],
            explain="""### 先分开“名字删了”和“对象没用了”
`del name` 删的是一个绑定，不是命令销毁对象。另一个变量、容器或闭包还握着它，它就依然可用。CPython 对普通对象做引用计数，最后一个强引用消失且没有特殊生命周期行为时，通常立即回收。但是对象甲指向乙、乙又指回甲，哪怕外面已经没有入口，环内部仍可能彼此撑住计数。

### 用弱引用观察一个环
```python
import gc
import weakref

class Node:
    pass

was_enabled = gc.isenabled()
gc.disable()
try:
    node = Node()
    node.peer = node
    watched = weakref.ref(node)
    del node
    assert watched() is not None
    gc.collect()
    assert watched() is None
finally:
    if was_enabled:
        gc.enable()
```

这里暂时关的是自动循环收集，不是引用计数，也不妨碍显式 `gc.collect()`。弱引用可观察对象但不会让它存活。把循环收集理解成候选对象上的“标记可达、清除不可达”：CPython 会计算扣除候选对象间内部引用后的计数，找出受到外部引用的候选对象，再沿引用关系追踪并保留可达对象，余下的不可达环才可能清理。不是所有对象都被跟踪，也不是每次从根开始扫整个堆。

### 为什么分代，以及怎么解释内存曲线
CPython 3.12 的循环收集器分三代；新纳入跟踪的对象进年轻代，存活的对象逐步晋升，老代检查更少。这样能把多数检查花在更可能很快失效的对象上。对象释放后，解释器或分配器还可能保留内存供复用，进程 RSS 不一定马上下降。反之，列表、缓存或全局注册表长期握着对象，哪怕主动收集也不能把仍可达的对象清掉。

### 面试怎么说
用“引用计数解决大多数，循环收集兜住不可达的环，分代减少扫描”概括原理；最后补一句文件和连接应使用 with 或显式清理，不把正确性绑定到 GC 时机。""",
            followups=[
                dict(q="显式 gc.collect() 之后内存不降能证明泄漏吗？", a="不能。对象可能仍由合法缓存持有，也可能已回收但分配器未把内存还给系统。先看稳定负载下对象和分配快照变化，再判断是引用保留还是常驻高水位。"),
                dict(q="为什么要用弱引用验证对象有没有释放？", a="为了观察而把对象放进普通列表会新增强引用，改变实验本身。用支持弱引用的对象做观察，既能查询当前是否仍存活，又不人为延长生命周期。"),
            ],
            pitfalls=["认为 del 必定立即销毁被引用对象。", "把循环收集说成对每个版本、每种 Python 实现都完全一样。"],
            hook="测开视角：怀疑回归反复运行后占用不断增长时，用合成负载跑多轮，观察对象与分配快照；复查缓存、任务回调和注册表的强引用。同时独立断言连接和文件显式释放，不从内存波动推断资源是否关闭。",
            mnemonic="计数管日常，循环靠追踪，三代分频查。",
        ),
        dict(
            id="py-arguments",
            q="*args、**kwargs 和解包怎么用，怎样限定关键字参数？",
            level=2,
            short="函数定义里 *args 收集剩余位置参数到元组，**kwargs 收集额外关键字到字典；调用时 *iterable 和 **mapping 则反过来展开。签名中 / 左边的参数只能按位置传，裸 * 或 *args 后面的普通参数须按关键字传。参数重复绑定、缺失或传给不接收它的签名会报 TypeError。",
            points=[
                "定义端 *args 收集为元组、**kwargs 收集为字典",
                "调用端 * 展开可迭代对象、** 展开键为字符串的映射",
                "区分 / 指定仅位置、* 指定仅关键字的参数",
                "理解同一个参数不能被位置值和关键字值重复绑定",
                "解释关键字参数如何增加可读性以及转发参数的用途",
            ],
            explain="""### 先看在定义处还是调用处
把 `*` 想成方向相反的两个操作：在函数签名中，它把剩余位置参数收成一包；在调用中，它把一包对象展开成多份实参。`**` 对关键字做类似事情。名字 `args` 和 `kwargs` 只是惯例，可以改；决定语义的是星号。混合使用时，解释器先按签名绑定参数，不允许同一个命名参数被绑定两次。

### 把测试任务的约束写在签名里
```python
def schedule(suite, /, *cases, timeout=2, **metadata):
    return suite, cases, timeout, metadata

case_ids = ["case-1", "case-2"]
settings = {"timeout": 5, "retry": 1}
suite, cases, timeout, metadata = schedule("smoke", *case_ids, **settings)
assert suite == "smoke"
assert cases == ("case-1", "case-2") and timeout == 5
assert metadata == {"retry": 1}

def next_attempt(attempt, *, limit):
    return attempt + 1 if attempt < limit else attempt

assert next_attempt(1, limit=2) == 2
```

`suite` 在 `/` 前，只接受位置绑定；`*cases` 承接任意数量额外位置参数，后面的 `timeout` 只接受按名绑定。没有剩余位置参数需要收集时，用一个裸 `*`，就像 `next_attempt` 的签名。带名字的 `limit` 在调用点比一个孤零零的数字好读；如果写 `next_attempt(1, 2)` 就会报错。`**settings` 的键必须是字符串，`schedule("smoke", timeout=3, **settings)` 会由于重复的 `timeout` 报错，不会后值覆盖。

### 转发何时好用，何时太宽松
装饰器不知道原函数完整签名时，可以用 `*args, **kwargs` 接再原样传下去；公开业务接口如果允许任意额外关键字，就可能把 `timout` 这种拼写悄悄吞入 metadata。关键业务选项适合显式签名，只有明确的扩展字段才通过映射接收，也可以再做白名单校验。`options = {**defaults, **overrides}` 是合并字典，后值可覆盖；调用时的参数绑定则不同。

### 面试怎么说
先指出“定义收集，调用展开”，再写一个带 `/` 或裸 `*` 的签名，说明从调用点怎么看出参数意义，最后用重复绑定说明错误分支。""",
            followups=[
                dict(q="函数中把 kwargs 的键删掉，会改掉原始映射吗？", a="调用展开后，函数收到的是用于收集额外关键字的字典，不是外面那个映射容器；但映射里的值对象没有自动深拷贝，原地改其中的列表仍可能影响调用者。"),
                dict(q="为什么超时这样的参数推荐仅关键字？", a="它让调用显式写 timeout，避免和位置上其他数字混淆，并给新增别的关键字选项留空间。不过改已有公开签名可能破坏使用位置参数的调用方。"),
            ],
            pitfalls=["把定义端的收集和调用端的解包方向说反。", "以为函数调用里重复的关键字像合并字典一样最后一个获胜。"],
            hook="测开视角：对封装调用的工具覆盖零个或多个位置参数、明确的仅关键字选项、拼错键和重复键。验证参数转发不改变原值，失败尽量在调用入口发生而不是让错误选项进入下游。",
            mnemonic="定义收包，调用拆包；斜线左按位置，星号后按名字。",
        ),
        dict(
            id="py-class-protocols",
            q="实例、类和静态方法怎么选？常见魔术方法有什么作用？",
            level=2,
            short="实例方法接 self，操作实例状态；类方法接 cls，常做可继承的备用构造；静态方法没有隐式首参，适合放与类相关的工具。property 把读取逻辑做成属性访问；__new__ 创建对象，__init__ 初始化，__repr__ 便于调试，__eq__ 和 __hash__ 需遵守相等对象有相同哈希的契约。鸭子类型按能力而非类型名使用对象。",
            points=[
                "分别说明实例方法、类方法、静态方法的隐式首参与适用场景",
                "用 property 表达有计算逻辑的属性访问，可只读也可定义 setter",
                "区分 __new__ 创建或返回对象与 __init__ 初始化现有对象",
                "说明 __repr__ 调试用途与 __eq__/__hash__ 相等哈希契约",
                "鸭子类型通过支持的方法或协议协作，不要求继承同一类",
            ],
            explain="""### 方法需要哪份上下文
看函数需要的数据：访问一个对象的状态就用实例方法，按调用的类构造对象就用类方法，与类有关联但不访问实例或类状态才用静态方法。`@property` 让访问者写 `case.label`，背后可以运行简单计算；它便于接口演进，但不要把有大量阻塞或副作用的任务伪装成一次普通属性访问。

### 一个可运行的小对象协议
```python
class CaseId(str):
    def __new__(cls, text):
        return super().__new__(cls, text.strip().lower())

class Case:
    def __init__(self, case_id):
        self.case_id = CaseId(case_id)

    @classmethod
    def from_row(cls, row):
        return cls(row["id"])

    @staticmethod
    def valid(text):
        return bool(text.strip())

    @property
    def label(self):
        return f"case:{self.case_id}"

    def __repr__(self):
        return f"Case({self.case_id!r})"

    def __eq__(self, other):
        if not isinstance(other, Case):
            return NotImplemented
        return self.case_id == other.case_id

    __hash__ = None

def describe(case_like):
    return case_like.label

class FakeCase:
    label = "case:fake"

case = Case.from_row({"id": " SMOKE "})
assert Case.valid(" SMOKE ") and case == Case("smoke")
assert repr(case) == "Case('smoke')"
assert describe(case) == "case:smoke" and describe(FakeCase()) == "case:fake"
```

字符串值不可变，所以规范化放在 `CaseId.__new__` 中创建字符串子类实例；普通 `Case` 的 `__init__` 是给已创建的实例填字段，不能返回另一个对象。`from_row` 用 `cls(...)`，适当的子类调用时可得到自己的类型。`__repr__` 便于观察内部 ID，`__eq__` 对不支持的类型返回 `NotImplemented` 让比较协议继续处理。

### 相等、哈希与鸭子类型各有契约
相等的可哈希对象必须有相同哈希，作为键期间相关字段不能改变。`Case` 的 ID 可重新赋值，所以让它不可哈希，若需要字典键可以用不可变的 `CaseId`。`describe` 只要求对象有 `label`，真实对象和替身不必有继承关系；这种按行为消费接口的写法就是鸭子类型。

### 面试怎么说
先讲三个方法分别收到什么，再用不可变字符串创建解释 new 和 init 的分工。最后用可变比较字段不能做稳定哈希键，以及测试替身只实现所需协议收尾。""",
            followups=[
                dict(q="定义了 __eq__ 但没定义 __hash__ 会怎样？", a="普通用户类定义自己的 __eq__ 而没显式提供 __hash__ 时，Python 通常将该类设为不可哈希。想成为哈希键，要明确维护相等与哈希契约，不能盲目沿用身份哈希。"),
                dict(q="类方法为什么不直接写 return Case(...)？", a="写死 Case 会让继承来的工厂总是返回基类对象。使用 cls 会根据实际调用的类构造实例，但子类仍要满足工厂假设的构造参数契约。"),
            ],
            pitfalls=["说 __init__ 创建并返回实例，混淆了 __new__ 和初始化。", "用可能变化的字段算哈希，还把实例放进集合长期使用。"],
            hook="测开视角：实现测试替身时只满足被测接口实际需要的属性或方法，并用真实实现补契约用例。对于作为字典键的业务对象，重点覆盖值相等与哈希一致性，以及可变字段不应参与键语义。",
            mnemonic="实例拿 self，类方法拿 cls；new 创建，init 填字段，协议看能力。",
        ),
        dict(
            id="py-exceptions",
            q="try、except、else、finally 怎么执行，异常该怎么设计？",
            level=2,
            short="try 放可能失败且需要处理的最小范围；异常发生时走匹配的 except，try 正常走完且未提前跳出时才走 else，finally 用来收尾，正常、异常或返回前通常都会执行。只捕获能处理的具体异常，可用自定义异常表达业务语义并用 raise ... from 保留根因；避免裸 except 吞掉退出和中断。",
            points=[
                "说出 try、匹配的 except、else、finally 在正常与异常路径的顺序",
                "else 只在 try 正常完成时执行，else 抛错不由同层 except 捕获",
                "自定义异常继承 Exception，并用 raise ... from 串接根因",
                "避免裸 except 和 finally 中的 return，保留异常与退出语义",
            ],
            explain="""### 异常不是统一兜底，而是类型化的失败信号
解析测试条数时，用户填的不是整数和存储服务不可用，是完全不同的故障。前者可提示用户修输入，后者应保留异常交给上层告警或按明确策略重试。`try` 越大，越容易误把后续逻辑的同类异常当成输入错误，所以只把可能出现且需要翻译的动作放进去。

### 正常和异常各走一遍
```python
class InvalidCount(ValueError):
    pass

def parse_count(raw, steps):
    try:
        count = int(raw)
    except ValueError as error:
        steps.append("except")
        raise InvalidCount("count must be an integer") from error
    else:
        steps.append("else")
        return count
    finally:
        steps.append("finally")

steps = []
assert parse_count("3", steps) == 3 and steps == ["else", "finally"]
steps.clear()
try:
    parse_count("bad", steps)
except InvalidCount as error:
    assert isinstance(error.__cause__, ValueError)
else:
    raise AssertionError("invalid data accepted")
assert steps == ["except", "finally"]
```

正常路径先运行 try，再走 else；即使 else 已决定返回，也先跑 finally。异常分支先找匹配的 except，再执行 finally，最后把新异常传播出去；没有匹配分支，也照样先做 finally。这里约定输入是字符串，程序员传错类型产生的 `TypeError` 不被包装成格式问题。若 try 用 return、break 等提前离开，else 不运行，finally 仍负责收尾。else 里的异常也不会倒回同一层 except。

### 哪些异常要让它继续传播
裸 `except:` 连 `KeyboardInterrupt` 和 `SystemExit` 等也会抓到，常导致任务停不下来；`except Exception` 也不应无条件吞掉，通常只适合作为日志或隔离边界并明确失败怎么上报。`raise` 可在处理分支重抛原异常，翻译到业务层时用 `raise NewError(...) from error` 保留链路。避免在 finally 里 `return`，否则它可能覆盖待返回的值，甚至压掉原异常；简洁的资源收尾通常优先用 `with`。

### 面试怎么说
先画正常、异常两条分支，再说自己只翻译预期的异常，保留根因，最后保证资源释放且不吞掉失败。""",
            followups=[
                dict(q="多个 except 的匹配顺序重要吗？", a="重要，按书写顺序选第一个匹配项；先写基类会让后面针对子类的处理无法到达。通常按从具体到一般写，并让每个分支负责清楚的恢复或上报动作。"),
                dict(q="为什么不能在 finally 里 return 一个兜底值？", a="在 finally 返回会替换原来正在返回的值，也可能截断待传播的异常，导致测试误报成功。应保留失败路径，只在 finally 做清理或必要记录。"),
            ],
            pitfalls=["把全部业务都塞进 try，再用裸 except 返回默认值。", "以为 finally 只在报错时经过，或认为 else 中的错误也由当前 except 处理。"],
            hook="测开视角：测试时分别注入实际能处理的输入错误、预期外系统错误和清理失败，检查异常类型、原因与资源状态。不要只断言出现错误，也要防止任何错误都被统一转换成成功响应。",
            mnemonic="try 缩小，except 精准，else 走正常，finally 只收尾。",
        ),
        dict(
            id="py-asyncio",
            q="async、await 和 asyncio.gather 怎么组织并发 I/O？",
            level=3,
            short="async def 定义协程函数，调用得到协程对象；await 等待可等待对象，未就绪时可让事件循环推进其他任务。gather 可并发安排多个协程，全部成功时按传入顺序返回结果。它适合大量可异步等待的 I/O，不会自动变成多核计算，也不会自动卸载同步阻塞调用。",
            points=[
                "区分协程函数、协程对象和事件循环中被调度的任务",
                "await 未就绪操作可以让出循环，多个等待得以重叠",
                "gather 全部成功时按输入顺序交付结果，不是完成顺序",
                "默认 gather 传播首个观察到的异常，不会因此自动取消其他任务",
                "知道异步 I/O、并发上限与阻塞调用的处理边界",
            ],
            explain="""### 让等待叠在一起，而不是一项一项等
巡检许多接口时，单个任务大部分时间在等响应，可以在这段等待期推进其他请求。`async def` 只定义如何执行；直接调用只得到协程对象，`asyncio.run` 从脚本入口启动事件循环并执行入口协程。在同一个循环里，一条任务拿到未完成的等待对象时可挂起，等条件满足再继续。它适合那些实现了异步接口的等待。

### 看清 gather 返回的顺序
```python
import asyncio

async def report(case_id, gate=None):
    if gate is not None:
        await gate.wait()
    return case_id

async def main():
    fast_done = asyncio.Event()

    async def fast():
        result = await report("second")
        fast_done.set()
        return result

    results = await asyncio.wait_for(
        asyncio.gather(report("first", fast_done), fast()), timeout=2
    )
    assert results == ["first", "second"]

asyncio.run(main())
```

第一项要等第二项发信号才有资格结束，结果还是按传入次序排列。单写 `await first()` 再 `await second()` 则是串行；如有这个例子的依赖顺序，甚至会永远等不到信号。`gather` 默认把先观察到的异常抛给等待方，但不会因某个子任务抛错就自动取消其他子任务；若事件循环继续运行，它们可能继续做事。需要组内失败时取消其他任务，可按需求选 `TaskGroup`；想逐项保留异常则可显式选 `return_exceptions=True` 并分类处理。

### 并发不等于没有容量上限
不要把大量输入一次全展开给 `gather`；可按批次处理或用有界队列限制在途任务，并设单调用及整批超时。把同步阻塞请求直接塞进协程会卡住循环，同步遗留 I/O 可考虑 `asyncio.to_thread`。默认 CPython 的 GIL 和多核选型见并发章，这里只记住异步主要是在复用等待时间。

### 面试怎么说
先报可异步等待的瓶颈，再展示 gather 收集顺序、失败的传播边界和并发限制，别只说给函数加上 async 就变快。""",
            followups=[
                dict(q="为什么交互环境里调用 asyncio.run 有时失败？", a="asyncio.run 要在当前线程尚无运行中事件循环时使用。在已运行循环的环境里，应使用环境支持的 await 或向现有循环提交工作，而不是再嵌套启动一个循环。"),
                dict(q="return_exceptions=True 能算失败处理完成吗？", a="它仅把子任务异常纳入结果序列，调用方仍要区分正常结果与异常，决定记录、告警或重试。否则容易让整批看似有正常响应，实际遗漏了失败用例。"),
            ],
            pitfalls=["假设 gather 结果按最快任务优先排列。", "以为某项异常传播后，其他任务一定都已经停止。"],
            hook="测开视角：用 Event 控制两个协程的先后，不靠睡眠猜完成顺序；再分别覆盖个别失败和整批超时，检查异常是否被汇总、在途请求有无越过限制，未完成任务是否按约定收尾。",
            mnemonic="调用得协程，await 可让出，gather 按输入收结果。",
        ),
        dict(
            id="py-pytest",
            q="pytest 的 fixture、参数化和 mock 怎么一起用？",
            level=1,
            short="pytest 按测试函数和 fixture 的参数名解析依赖，先装配再运行测试，yield 后做清理。默认作用域是 function，也可用 class、module、package、session 管复用范围；目录共享 fixture 可放 conftest.py，无需手动导入。parametrize 把一张数据表展开为独立用例，patch 要替换被测代码实际查找的名字。",
            points=[
                "解释 fixture 按参数名注入、可依赖其他 fixture、yield 用于清理",
                "说出默认及其他作用域，理解复用会影响状态隔离",
                "conftest.py 提供目录树内共享 fixture，无需测试文件显式导入",
                "parametrize 把参数集合变成独立用例项，便于单独报告或重跑",
                "unittest.mock.patch 替换使用方查找位置，并验证调用参数和次数",
            ],
            explain="""### 把环境、数据与外部副作用分开
测试发送提醒的逻辑，不应让每次运行真的连接外部服务。fixture 准备独立状态并清理，参数化覆盖提醒和不提醒两个分支，patch 替换真实发送动作。这样一次失败能具体到某组输入，还能断言外部动作是否发生，不只检查返回码。pytest 根据测试函数的形参找到 fixture，fixture 本身也能按同样方式声明依赖。

### 一个文件从装配到断言
把代码存为 `test_alert.py`，运行 `pytest -q test_alert.py`：

```python
from unittest.mock import patch

import pytest

def send(message):
    raise RuntimeError("real delivery must not run in these tests")

def alert(score, state):
    if score < state["threshold"]:
        send("low score")
        return True
    return False

@pytest.fixture
def state():
    settings = {"threshold": 60}
    yield settings
    settings.clear()

@pytest.mark.parametrize(
    "score, expected", [(59, True), (60, False)], ids=["below", "boundary"]
)
def test_alert(score, expected, state):
    with patch(f"{__name__}.send", autospec=True) as mocked_send:
        assert alert(score, state) is expected
        if expected:
            mocked_send.assert_called_once_with("low score")
        else:
            mocked_send.assert_not_called()
```

pytest 收集两项独立测试，每项默认拿一份新的 state；fixture 成功执行到 `yield` 后，即使测试断言失败也会走后置清理。对于外部资源，要注册真实关闭动作；如果在 `yield` 前申请多个资源，要另处理部分成功、后续失败的回退。共享 fixture 可以放在上层 `conftest.py`，供该目录及其子目录发现。scope 决定生命周期：可从默认 function 扩到 class、module、package 或 session，不等于所有状态都应跨用例共享。可变数据尽量保持 function，新建成本高且可安全复用的资源才考虑更宽范围。

### patch 应该替换哪里
本例 `alert` 从自己模块的全局名字 `send` 查找，所以 patch 本模块。如果模块 `alerts` 用 `from transport import send`，通常该 patch 的是 `alerts.send`，不是定义处 `transport.send`；名字在导入时已经绑定。`autospec=True` 让替身检查调用签名，`with` 退出后恢复原绑定。单测可用 mock 隔离，接口协议仍要有集成用例验证，避免替身与真实系统渐渐偏离。

### 面试怎么说
拿一条边界用例串起依赖装配、参数展开和交互断言。最后能解释为什么 patch 用那条路径，以及为什么状态 fixture 不用 session。""",
            followups=[
                dict(q="scope 改成 session 就一定只初始化一次吗？", a="非参数化 fixture 在单个测试进程的该会话范围内通常复用，但参数化可能按不同参数创建实例，多进程执行也不是共享同一进程内的对象。不能靠扩大作用域跨进程共享状态。"),
                dict(q="为什么 parametrize 传可变数据也可能相互污染？", a="参数对象不会因参数化自动深拷贝。若不同用例拿到同一个列表或字典，其中一个修改后别的用例可能读到变化；应在 fixture 或工厂中为每项创建独立状态。"),
            ],
            pitfalls=["在被测模块已经绑定名称后，还去定义处 patch，真实调用没有被拦住。", "为提速把所有夹具都升到 session，导致可变状态和清理相互干扰。"],
            hook="测开视角：用 fixture 提供可复位测试数据，用参数化精确标记边界和错误场景，再用 autospec 与调用断言检查副作用。把少量真实连接的集成测试和隔离单测分层，分别保证协议与分支正确。",
            mnemonic="fixture 管环境，参数化管数据，patch 换查找点。",
        ),
    ],
)
