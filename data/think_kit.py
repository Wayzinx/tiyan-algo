# 「思路 · 盲写基本功」：刷题时最常用、最容易卡壳的 Python 写法，每个都要能闭眼写出来
# 每题：id / title / use（刷题里什么时候用）/ prompt / starter / solution / tests（test_ 函数）/ tip（关键 API）
# gen_think.py 校验：solution 通过全部测试，starter 至少挂一个
K = []


def kit(id, title, use, prompt, starter, solution, tests, tip):
    K.append(dict(id=id, title=title, use=use, prompt=prompt, starter=starter.strip() + "\n", solution=solution.strip() + "\n", tests=tests.strip() + "\n", tip=tip))


kit("count", "计数：每个元素出现几次", "两数之和变体、字母异位词、Top K、众数……一半的题第一步都是计数。",
    "实现 `count_words(words)`：返回 dict，键是单词，值是出现次数。分别想想用 `dict.get`、`defaultdict(int)`、`Counter` 三种写法。",
    """
def count_words(words):
    # 返回 {单词: 次数}
    pass
""", """
from collections import Counter

def count_words(words):
    return dict(Counter(words))
""", """
def test_basic():
    assert count_words(["a", "b", "a", "c", "a"]) == {"a": 3, "b": 1, "c": 1}

def test_empty():
    assert count_words([]) == {}
""", "cnt[x] = cnt.get(x, 0) + 1；或 cnt = defaultdict(int); cnt[x] += 1；或 Counter(words)")

kit("topk-sort", "Top K：按次数降序、同次数按字典序", "高频元素 / 高频路线 / 排行榜：排序键写成元组，降序的那一项取负。",
    "实现 `top_k(words, k)`：返回出现次数最多的 k 个单词；次数相同按字母序升序。先用 `sorted(..., key=...)` 写一遍。",
    """
def top_k(words, k):
    pass
""", """
from collections import Counter

def top_k(words, k):
    cnt = Counter(words)
    return [w for w, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]
""", """
def test_order():
    assert top_k(["b", "a", "c", "a", "b", "d"], 2) == ["a", "b"]

def test_tie_by_alpha():
    assert top_k(["z", "y", "x"], 3) == ["x", "y", "z"]

def test_k_larger():
    assert top_k(["a"], 5) == ["a"]
""", "key=lambda kv: (-kv[1], kv[0])：元组逐项比较，-次数 让次数大的排前面")

kit("heap-kth", "堆：第 k 大的数", "第 k 大 / 前 k 个 / 数据流：维护一个大小为 k 的小顶堆，堆顶就是第 k 大。",
    "实现 `kth_largest(nums, k)`，用 `heapq`，不要整体排序：维护大小为 k 的小顶堆。",
    """
import heapq

def kth_largest(nums, k):
    pass
""", """
import heapq

def kth_largest(nums, k):
    heap = []
    for x in nums:
        heapq.heappush(heap, x)
        if len(heap) > k:
            heapq.heappop(heap)
    return heap[0]
""", """
def test_basic():
    assert kth_largest([3, 2, 1, 5, 6, 4], 2) == 5

def test_dup():
    assert kth_largest([3, 2, 3, 1, 2, 4, 5, 5, 6], 4) == 4

def test_one():
    assert kth_largest([7], 1) == 7
""", "heapq 只有小顶堆：heappush / heappop / heap[0] 是最小值；超过 k 个就弹出最小的")

kit("heap-tuple", "堆里放元组：按 (优先级, 名字) 出队", "Dijkstra、合并 k 个有序链表、任务调度：堆里放 (比较键, 数据)。",
    "实现 `order(tasks)`：tasks 是 `[(名字, 优先级)]`，优先级数字越大越先做，同优先级按名字字母序。用 heapq 依次弹出，返回名字列表。",
    """
import heapq

def order(tasks):
    pass
""", """
import heapq

def order(tasks):
    heap = [(-p, name) for name, p in tasks]
    heapq.heapify(heap)
    out = []
    while heap:
        _, name = heapq.heappop(heap)
        out.append(name)
    return out
""", """
def test_priority():
    assert order([("a", 1), ("b", 3), ("c", 2)]) == ["b", "c", "a"]

def test_tie():
    assert order([("y", 5), ("x", 5), ("z", 1)]) == ["x", "y", "z"]

def test_empty():
    assert order([]) == []
""", "大顶堆 = 存负数；元组 (-优先级, 名字) 先比第一项再比第二项；heapify 原地建堆 O(n)")

kit("nlargest", "一行 Top K：heapq.nlargest / nsmallest", "数据量不大时最省事；key 参数和 sorted 一样用。",
    "实现 `top_routes(cnt, k)`：cnt 是 `{(起点, 终点): 次数}`，返回次数最多的 k 条路线（元组），同次数按路线字典序升序。用 `heapq.nsmallest` 加 key 写一行。",
    """
import heapq

def top_routes(cnt, k):
    pass
""", """
import heapq

def top_routes(cnt, k):
    return [r for r, _ in heapq.nsmallest(k, cnt.items(), key=lambda kv: (-kv[1], kv[0]))]
""", """
def test_basic():
    cnt = {("A", "B"): 3, ("C", "D"): 2, ("A", "C"): 1}
    assert top_routes(cnt, 2) == [("A", "B"), ("C", "D")]

def test_tie():
    cnt = {("B", "C"): 2, ("A", "Z"): 2}
    assert top_routes(cnt, 1) == [("A", "Z")]
""", "nsmallest(k, iterable, key=...)：key 写 (-次数, 路线)，就是“次数大的优先、再按字典序”")

kit("normalize", "规范化 key：无向的 A-B 和 B-A 算同一个", "无向边去重、字母异位词分组、路线统计：先把等价的东西变成同一个 key。",
    "实现 `count_routes(routes)`：routes 是 `[[a, b], ...]`，A→B 与 B→A 算同一条，a == b 的忽略。返回 `{(小, 大): 次数}`。",
    """
def count_routes(routes):
    pass
""", """
from collections import Counter

def count_routes(routes):
    cnt = Counter()
    for a, b in routes:
        if a != b:
            cnt[(min(a, b), max(a, b))] += 1
    return dict(cnt)
""", """
def test_merge_direction():
    assert count_routes([["A", "B"], ["B", "A"], ["A", "C"]]) == {("A", "B"): 2, ("A", "C"): 1}

def test_skip_self():
    assert count_routes([["x", "x"], ["y", "x"]]) == {("x", "y"): 1}
""", "key = (min(a, b), max(a, b)) 或 tuple(sorted((a, b)))；list 不能当 dict 的键，要用 tuple")

kit("group", "分组：defaultdict(list)", "字母异位词分组、按某属性聚合、建图的邻接表。",
    "实现 `group_by_sorted(strs)`：把字母组成相同的单词分到一组，返回 dict：键是排好序的字母串，值是原单词列表（保持出现顺序）。",
    """
def group_by_sorted(strs):
    pass
""", """
from collections import defaultdict

def group_by_sorted(strs):
    g = defaultdict(list)
    for s in strs:
        g["".join(sorted(s))].append(s)
    return dict(g)
""", """
def test_basic():
    assert group_by_sorted(["eat", "tea", "tan", "ate"]) == {"aet": ["eat", "tea", "ate"], "ant": ["tan"]}

def test_empty_str():
    assert group_by_sorted([""]) == {"": [""]}
""", "defaultdict(list)：访问不存在的键时自动给空列表；sorted(s) 返回字符列表，要 ''.join")

kit("sort-multi", "多关键字排序", "区间按起点排序、按分数降序再按名字升序、自定义比较。",
    "实现 `rank(students)`：students 是 `[(名字, 分数, 年龄)]`，按分数降序，分数相同按年龄升序，再相同按名字升序，返回名字列表。",
    """
def rank(students):
    pass
""", """
def rank(students):
    return [n for n, s, a in sorted(students, key=lambda x: (-x[1], x[2], x[0]))]
""", """
def test_rank():
    st = [("bob", 90, 20), ("amy", 95, 22), ("cat", 90, 19), ("dan", 90, 19)]
    assert rank(st) == ["amy", "cat", "dan", "bob"]
""", "key 返回元组；数字降序取负；字符串降序不能取负，可以用 sorted(..., reverse=True) 分两次稳定排序")

kit("bfs", "BFS：网格最短步数（deque）", "最短步数、扩散、层序遍历：队列 + 访问标记，出队时处理、入队时标记。",
    "实现 `min_steps(grid)`：grid 是 0/1 网格（1 是墙），从左上角走到右下角，只能上下左右，返回最少步数；走不到返回 -1。",
    """
from collections import deque

def min_steps(grid):
    pass
""", """
from collections import deque

def min_steps(grid):
    n, m = len(grid), len(grid[0])
    if grid[0][0] or grid[n - 1][m - 1]:
        return -1
    q = deque([(0, 0, 0)])
    seen = {(0, 0)}
    while q:
        r, c, d = q.popleft()
        if (r, c) == (n - 1, m - 1):
            return d
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < m and not grid[nr][nc] and (nr, nc) not in seen:
                seen.add((nr, nc))
                q.append((nr, nc, d + 1))
    return -1
""", """
def test_open():
    assert min_steps([[0, 0, 0], [0, 0, 0]]) == 3

def test_wall():
    assert min_steps([[0, 1], [1, 0]]) == -1

def test_detour():
    assert min_steps([[0, 0, 0], [1, 1, 0], [0, 0, 0]]) == 4

def test_single():
    assert min_steps([[0]]) == 0
""", "deque.popleft() 是 O(1)（list.pop(0) 是 O(n)）；入队时就加入 seen，避免重复入队")

kit("stack", "栈：括号匹配", "括号、表达式、撤销、单调栈的基础：list 的 append / pop 就是栈。",
    "实现 `valid(s)`：s 只含 `()[]{}`，判断括号是否有效配对。",
    """
def valid(s):
    pass
""", """
def valid(s):
    pair = {")": "(", "]": "[", "}": "{"}
    st = []
    for ch in s:
        if ch in pair:
            if not st or st.pop() != pair[ch]:
                return False
        else:
            st.append(ch)
    return not st
""", """
def test_ok():
    assert valid("()[]{}") and valid("{[()]}") and valid("")

def test_bad():
    assert not valid("(]") and not valid("([)]") and not valid("((")

def test_close_first():
    assert not valid(")(")
""", "右括号来了就和栈顶比；最后栈要为空；空栈 pop 会报错，先判断")

kit("two-ptr", "双指针：原地去重 / 判回文", "有序数组去重、移动零、反转、判回文：一个读、一个写，或者两头往中间走。",
    "实现 `is_pal(s)`：只考虑字母和数字、忽略大小写，判断是否回文。用左右双指针，不要生成新字符串。",
    """
def is_pal(s):
    pass
""", """
def is_pal(s):
    l, r = 0, len(s) - 1
    while l < r:
        if not s[l].isalnum():
            l += 1
        elif not s[r].isalnum():
            r -= 1
        elif s[l].lower() != s[r].lower():
            return False
        else:
            l += 1
            r -= 1
    return True
""", """
def test_yes():
    assert is_pal("A man, a plan, a canal: Panama")

def test_no():
    assert not is_pal("race a car")

def test_empty():
    assert is_pal("") and is_pal(" ,")
""", "while l < r；跳过非字母数字用 str.isalnum()；比较用 .lower()")

kit("window", "滑动窗口：固定长度 k 的最大和", "定长窗口：进一个、出一个，维护窗口和；不定长窗口：右边进、不合法缩左边。",
    "实现 `max_sum_k(nums, k)`：返回长度为 k 的连续子数组的最大和（保证 1 ≤ k ≤ len(nums)），要求 O(n)。",
    """
def max_sum_k(nums, k):
    pass
""", """
def max_sum_k(nums, k):
    cur = sum(nums[:k])
    best = cur
    for i in range(k, len(nums)):
        cur += nums[i] - nums[i - k]
        best = max(best, cur)
    return best
""", """
def test_basic():
    assert max_sum_k([1, 4, 2, 10, 2, 3, 1, 0, 20], 4) == 24

def test_neg():
    assert max_sum_k([-3, -1, -2], 2) == -3

def test_whole():
    assert max_sum_k([5, 1], 2) == 6
""", "新窗口和 = 旧和 + 进来的 nums[i] - 出去的 nums[i-k]；best 初值用第一个窗口，不要用 0（全负数会错）")

kit("prefix", "前缀和：多次区间求和", "区间和、和为 k 的子数组：pre[i] 表示前 i 个数的和，区间和 = pre[r+1] - pre[l]。",
    "实现 `range_sums(nums, queries)`：queries 是 `[(l, r)]`（闭区间），返回每个区间的和。先建前缀和数组再 O(1) 回答。",
    """
def range_sums(nums, queries):
    pass
""", """
def range_sums(nums, queries):
    pre = [0]
    for x in nums:
        pre.append(pre[-1] + x)
    return [pre[r + 1] - pre[l] for l, r in queries]
""", """
def test_basic():
    assert range_sums([1, 2, 3, 4], [(0, 3), (1, 2), (2, 2)]) == [10, 5, 3]

def test_neg():
    assert range_sums([-1, 5, -2], [(0, 1), (0, 2)]) == [4, 2]
""", "pre 比 nums 多一个 0 开头，避免 l = 0 时特判；闭区间 [l, r] 的和是 pre[r+1] - pre[l]")

kit("bisect", "二分：bisect 找位置", "有序数组里找插入位置、统计 ≤ x 的个数、最长递增子序列的 O(n log n) 写法。",
    "实现 `count_le(sorted_nums, x)`：返回有序数组里 ≤ x 的元素个数；再想想 < x 的个数怎么写。",
    """
import bisect

def count_le(sorted_nums, x):
    pass
""", """
import bisect

def count_le(sorted_nums, x):
    return bisect.bisect_right(sorted_nums, x)
""", """
def test_basic():
    assert count_le([1, 2, 2, 2, 5], 2) == 4

def test_edges():
    assert count_le([1, 3], 0) == 0 and count_le([1, 3], 9) == 2 and count_le([], 1) == 0
""", "bisect_left：第一个 ≥ x 的位置（= 小于 x 的个数）；bisect_right：第一个 > x 的位置（= ≤ x 的个数）")

kit("grid2d", "二维数组：别用 [[0]*m]*n", "DP 表、网格、邻接矩阵。乘法复制的是同一行的引用，改一行全变。",
    "实现 `make_grid(n, m)`：返回 n 行 m 列、全是 0 的二维列表，并且每行是独立的列表。",
    """
def make_grid(n, m):
    return [[0] * m] * n   # 这样写对吗？
""", """
def make_grid(n, m):
    return [[0] * m for _ in range(n)]
""", """
def test_shape():
    g = make_grid(3, 4)
    assert len(g) == 3 and all(len(r) == 4 for r in g)

def test_independent_rows():
    g = make_grid(3, 4)
    g[0][0] = 1
    assert g[1][0] == 0 and g[2][0] == 0
""", "[[0] * m for _ in range(n)]：推导式每次新建一行；[[0]*m]*n 的 n 行是同一个对象")

kit("memo", "记忆化递归：@cache", "动态规划的“自顶向下”写法：先写出递归，再加 @cache 去掉重复子问题。",
    "实现 `ways(n)`：爬楼梯，每次爬 1 或 2 级，到第 n 级（n ≤ 80）有多少种走法。先写递归，再加 `functools.cache`。",
    """
def ways(n):
    pass
""", """
from functools import cache

@cache
def ways(n):
    if n <= 1:
        return 1
    return ways(n - 1) + ways(n - 2)
""", """
def test_small():
    assert [ways(i) for i in range(1, 6)] == [1, 2, 3, 5, 8]

def test_big():
    assert ways(80) == 37889062373143906
""", "@cache 把 (参数 → 结果) 存起来；参数必须可哈希（list 要转 tuple）；递归太深时改成循环递推")

kit("linked", "链表：反转", "链表题基本功：三个指针 prev / cur / nxt，先存下一个，再改指向。",
    "实现 `reverse(head)`：反转单链表并返回新头节点。题目已给出 `ListNode`。",
    """
class ListNode:
    def __init__(self, val=0, next=None):
        self.val, self.next = val, next

def reverse(head):
    pass
""", """
class ListNode:
    def __init__(self, val=0, next=None):
        self.val, self.next = val, next

def reverse(head):
    prev, cur = None, head
    while cur:
        nxt = cur.next
        cur.next = prev
        prev, cur = cur, nxt
    return prev
""", """
def build(vals):
    head = None
    for v in reversed(vals):
        head = ListNode(v, head)
    return head

def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out

def test_basic():
    assert to_list(reverse(build([1, 2, 3, 4]))) == [4, 3, 2, 1]

def test_empty_one():
    assert reverse(None) is None and to_list(reverse(build([7]))) == [7]
""", "顺序：nxt = cur.next → cur.next = prev → prev = cur → cur = nxt；返回 prev")

kit("str", "字符串常用操作", "反转单词、计数数组、拼接：字符串不可变，拼很多次要用列表再 join。",
    "实现 `reverse_words(s)`：把句子里的单词顺序反转，多个空格当一个，首尾空格去掉。例如 `'  the sky  is blue '` → `'blue is sky the'`。",
    """
def reverse_words(s):
    pass
""", """
def reverse_words(s):
    return " ".join(reversed(s.split()))
""", """
def test_basic():
    assert reverse_words("the sky is blue") == "blue is sky the"

def test_spaces():
    assert reverse_words("  hello   world  ") == "world hello"
""", "s.split() 不带参数会按任意空白切并丢掉空串；' '.join(list)；reversed() 或切片 [::-1]")

KIT = K
