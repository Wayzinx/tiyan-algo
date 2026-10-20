import random
from textwrap import dedent


def _code(s):
    return dedent(s).strip() + "\n"


def _ints(seed, n, lo=-1000, hi=1000):
    r = random.Random(seed)
    return [r.randint(lo, hi) for _ in range(n)]


def _str(seed, n, alphabet="abc"):
    r = random.Random(seed)
    return "".join(r.choice(alphabet) for _ in range(n))


def _words(seed, n, alphabet="abcde", min_len=1, max_len=6):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        k = r.randint(min_len, max_len)
        w = "".join(r.choice(alphabet) for _ in range(k))
        if r.random() < 0.45:
            w = "".join(r.sample(w, len(w)))
        out.append(w)
    return out


def _two_sum_case(seed, n):
    r = random.Random(seed)
    nums = []
    for _ in range(n):
        x = r.randint(-10**6, 10**6) * 2
        if x == 2:
            x = 4
        nums.append(x)
    return [nums + [1, 2], 3]


def _matrix(seed, rows, cols, values):
    r = random.Random(seed)
    return [[r.choice(values) for _ in range(cols)] for _ in range(rows)]


def _sorted(seed, n, lo=-1000, hi=1000):
    return sorted(_ints(seed, n, lo, hi))


def _topk_case(seed, distinct=60, k=10):
    arr = []
    for v in range(distinct):
        arr.extend([v] * (distinct - v))
    random.Random(seed).shuffle(arr)
    return [arr, k]


def _intervals(seed, n, lo=0, hi=10000, max_width=20):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        start = r.randint(lo, hi - max_width)
        out.append([start, start + r.randint(0, max_width)])
    return out


def _erase_intervals(seed, n):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        a, b = r.randint(-5000, 5000), r.randint(-5000, 5000)
        out.append([min(a, b), max(a, b) + 1])
    return out


def _jumps(seed, n):
    r = random.Random(seed)
    return [r.randint(0, 5) for _ in range(n)]


def _bst_level(vals):
    arr = []
    def put(lo, hi, idx):
        if lo > hi:
            return
        mid = (lo + hi) // 2
        while len(arr) <= idx:
            arr.append(None)
        arr[idx] = vals[mid]
        put(lo, mid - 1, idx * 2 + 1)
        put(mid + 1, hi, idx * 2 + 2)
    put(0, len(vals) - 1, 0)
    while arr and arr[-1] is None:
        arr.pop()
    return arr


def _grid_islands(seed, rows, cols):
    r = random.Random(seed)
    return [["1" if r.random() < 0.38 else "0" for _ in range(cols)] for _ in range(rows)]


def P(id, title, pattern, level, lc, desc, examples, constraints, fn, params, ret, tests, solution, complexity, hints, key, pitfalls, types=None, ret_type=None, compare="exact"):
    return dict(id=id, title=title, pattern=pattern, level=level, lc=lc, slug=id, desc=desc, examples=examples,
                constraints=constraints, fn=fn, params=params, ret=ret, types=types, ret_type=ret_type,
                compare=compare, tests=tests, solution=_code(solution), complexity=complexity,
                hints=hints, key=key, pitfalls=pitfalls)


PROBLEMS = [
    P(
        "two-sum", "两数之和", "hash", "easy", 1,
        "给你一个整数数组 `nums` 和一个目标值 `target`，在数组里找出**和为 target 的两个数**，返回它们的下标。\n\n题目保证恰好有一组答案，同一个元素不能用两次，下标顺序随意。",
        [
            {"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "note": "nums[0] + nums[1] = 2 + 7 = 9"},
            {"input": "nums = [3,3], target = 6", "output": "[0,1]", "note": ""},
        ],
        ["2 <= len(nums) <= 10^4", "-10^9 <= nums[i], target <= 10^9", "只存在一个有效答案"],
        "twoSum", [("nums", "List[int]"), ("target", "int")], "List[int]",
        [
            [[2, 7, 11, 15], 9], [[3, 3], 6], [[3, 2, 4], 6], [[-1, -2, -3, -4, -5], -8],
            [[0, 4, 3, 0], 0], [[1, 5, 9, 13], 22], [[-10**9, 5, 10**9], 0], _two_sum_case(1, 1500),
        ],
        """
        class Solution:
            def twoSum(self, nums, target):
                seen = {}
                for i, x in enumerate(nums):
                    if target - x in seen:
                        return [seen[target - x], i]
                    seen[x] = i
        """,
        "时间 O(n)，空间 O(n)",
        ["题型：哈希表。暴力是两层循环 O(n²)，瓶颈在于反复找另一个数。", "遍历时保存 `值 -> 下标`，当前数只需要查一次补数是否出现过。", "先查 `target - x`，再存当前 `x`，避免把同一个位置配给自己。"],
        "反复查找补数时，用哈希表把查找降到 O(1)。",
        ["先存后查会在 `nums=[3]` 类思路里误用自己，合法用例中也容易返回重复下标", "用 `nums.index()` 找补数会退化成 O(n²)"] ,
        compare="unordered",
    ),
    P(
        "group-anagrams", "字母异位词分组", "hash", "medium", 49,
        "给定字符串数组 `strs`，把由相同字母重新排列得到的字符串放进同一组。\n\n返回所有分组，组与组、组内字符串的顺序都不作为判断重点。",
        [
            {"input": "strs = ['eat','tea','tan','ate','nat','bat']", "output": "[['eat','tea','ate'],['tan','nat'],['bat']]", "note": "每组字符计数相同"},
            {"input": "strs = ['']", "output": "[['']]", "note": "空字符串也是一个分组"},
        ],
        ["1 <= len(strs) <= 10^4", "0 <= len(strs[i]) <= 100", "strs[i] 只包含小写英文字母"],
        "groupAnagrams", [("strs", "List[str]")], "List[List[str]]",
        [
            [["eat", "tea", "tan", "ate", "nat", "bat"]], [[""]], [["a"]], [["", "", "a"]],
            [["abc", "bca", "cab", "foo", "ofo", "bar"]], [["dddd", "dd", "d"]], [_words(2, 220)], [_words(3, 260, "abcdef", 2, 7)],
        ],
        """
        class Solution:
            def groupAnagrams(self, strs):
                groups = defaultdict(list)
                for s in strs:
                    groups[tuple(sorted(s))].append(s)
                return list(groups.values())
        """,
        "时间 O(n k log k)，空间 O(nk)",
        ["题型：哈希分组。异位词的信号是“字母重排后相同”，暴力两两比较太慢。", "为每个字符串计算一个不会受排列影响的签名，例如排序后的字符元组。", "遍历 `strs`，把签名作为字典键，把原字符串追加到对应列表。"],
        "异位词共享同一个规范化签名，用签名做哈希分组。",
        ["直接用原字符串做键会把 `eat` 和 `tea` 分到不同组", "返回顺序不固定，判题需要按无序嵌套比较"],
        compare="unordered_deep",
    ),
    P(
        "longest-consecutive-sequence", "最长连续序列", "hash", "medium", 128,
        "给定未排序整数数组 `nums`，求能够连成连续整数的最长序列长度。\n\n序列不要求在原数组里相邻，重复数字只算一次。",
        [
            {"input": "nums = [100,4,200,1,3,2]", "output": "4", "note": "最长是 1,2,3,4"},
            {"input": "nums = [0,3,7,2,5,8,4,6,0,1]", "output": "9", "note": "0 到 8 连续"},
        ],
        ["0 <= len(nums) <= 10^5", "-10^9 <= nums[i] <= 10^9", "需要接近 O(n) 的做法"],
        "longestConsecutive", [("nums", "List[int]")], "int",
        [
            [[100, 4, 200, 1, 3, 2]], [[0, 3, 7, 2, 5, 8, 4, 6, 0, 1]], [[]], [[1]],
            [[1, 2, 2, 3]], [[-2, -1, 0, 1, 100]], [[10, 9, 8, 1, 2]], [_ints(4, 1800, -2000, 2000) + list(range(5000, 6200))],
        ],
        """
        class Solution:
            def longestConsecutive(self, nums):
                s = set(nums)
                best = 0
                for x in s:
                    if x - 1 not in s:
                        y = x
                        while y in s:
                            y += 1
                        best = max(best, y - x)
                return best
        """,
        "时间 O(n)，空间 O(n)",
        ["题型：哈希集合。未排序还要求连续，排序会多出 O(n log n)。", "只从“没有前驱”的数字开始扩展，保证每段连续区间只扫描一次。", "把 `nums` 放入集合；若 `x-1` 不存在，就不断找 `x,x+1,...` 更新答案。"],
        "只从连续段起点向右数，避免每个数字都重复扩展。",
        ["从每个数字都向右扩展会在长连续数组上退化", "忘记去重会让重复数字干扰长度统计"],
    ),
    P(
        "container-with-most-water", "盛最多水的容器", "two_pointers", "medium", 11,
        "数组 `height` 表示每条竖线的高度，任选两条线和横轴组成容器。\n\n返回容器能装的最大水量，面积由较短高度乘以两线距离决定。",
        [
            {"input": "height = [1,8,6,2,5,4,8,3,7]", "output": "49", "note": "下标 1 和 8 组成最大面积"},
            {"input": "height = [1,1]", "output": "1", "note": "只有一种选择"},
        ],
        ["2 <= len(height) <= 10^5", "0 <= height[i] <= 10^4", "返回值在整数范围内"],
        "maxArea", [("height", "List[int]")], "int",
        [
            [[1,8,6,2,5,4,8,3,7]], [[1,1]], [[4,3,2,1,4]], [[1,2,1]],
            [[0,0,0,0]], [[1,2,3,4,5,6]], [[6,5,4,3,2,1]], [_ints(5, 1800, 0, 10000)],
        ],
        """
        class Solution:
            def maxArea(self, height):
                left, right = 0, len(height) - 1
                ans = 0
                while left < right:
                    ans = max(ans, min(height[left], height[right]) * (right - left))
                    if height[left] < height[right]:
                        left += 1
                    else:
                        right -= 1
                return ans
        """,
        "时间 O(n)，空间 O(1)",
        ["题型：双指针。暴力枚举两条线是 O(n²)，瓶颈在所有配对。", "面积受短板限制；移动高板不会改善当前短板，只可能损失宽度。", "左右指针从两端开始，每次记录面积并移动高度较小的一侧。"],
        "宽度递减时，只移动短板才可能得到更高的有效高度。",
        ["移动较高指针会错过答案", "面积要乘距离 `right-left`，不是下标数量"],
    ),
    P(
        "3sum", "三数之和", "two_pointers", "medium", 15,
        "给定整数数组 `nums`，找出所有不重复三元组，使三数之和为 0。\n\n同一个下标不能重复使用，答案中不能出现值完全相同的三元组。",
        [
            {"input": "nums = [-1,0,1,2,-1,-4]", "output": "[[-1,-1,2],[-1,0,1]]", "note": "重复三元组只保留一次"},
            {"input": "nums = [0,0,0]", "output": "[[0,0,0]]", "note": "三个零可以组成一个答案"},
        ],
        ["3 <= len(nums) <= 3000", "-10^5 <= nums[i] <= 10^5", "答案不能包含重复三元组"],
        "threeSum", [("nums", "List[int]")], "List[List[int]]",
        [
            [[-1,0,1,2,-1,-4]], [[0,0,0]], [[0,1,1]], [[-2,0,1,1,2]],
            [[-4,-2,-2,-2,0,1,2,2,3,3,4]], [[1,2,-2,-1]], [[0]*20], [[i + 1 for i in range(1200)]],
        ],
        """
        class Solution:
            def threeSum(self, nums):
                nums.sort()
                ans = []
                n = len(nums)
                for i in range(n - 2):
                    if i and nums[i] == nums[i - 1]:
                        continue
                    if nums[i] > 0:
                        break
                    left, right = i + 1, n - 1
                    while left < right:
                        total = nums[i] + nums[left] + nums[right]
                        if total == 0:
                            ans.append([nums[i], nums[left], nums[right]])
                            left += 1
                            right -= 1
                            while left < right and nums[left] == nums[left - 1]:
                                left += 1
                            while left < right and nums[right] == nums[right + 1]:
                                right -= 1
                        elif total < 0:
                            left += 1
                        else:
                            right -= 1
                return ans
        """,
        "时间 O(n²)，空间 O(1)（不计答案）",
        ["题型：排序 + 双指针。暴力三层循环是 O(n³)，瓶颈在枚举后两数。", "固定一个数后，剩余问题变成有序数组里的两数和。", "排序后跳过重复固定值；左右指针根据和太小或太大移动，命中后两边都去重。"],
        "排序后固定一数，把三数和降成双指针两数和。",
        ["不跳过重复会输出重复三元组", "命中后只移动一边可能死循环或重复", "提前 `nums[i] > 0` 只在排序后成立"],
        compare="unordered_deep",
    ),
    P(
        "trapping-rain-water", "接雨水", "two_pointers", "hard", 42,
        "数组 `height` 表示柱子的高度，雨后每个位置能接多少水由左右最高柱决定。\n\n返回所有位置能接到的雨水总量。",
        [
            {"input": "height = [0,1,0,2,1,0,1,3,2,1,2,1]", "output": "6", "note": "多个低洼位置累计为 6"},
            {"input": "height = [4,2,0,3,2,5]", "output": "9", "note": "右侧高柱封住水位"},
        ],
        ["1 <= len(height) <= 2 * 10^4", "0 <= height[i] <= 10^5", "结果在整数范围内"],
        "trap", [("height", "List[int]")], "int",
        [
            [[0,1,0,2,1,0,1,3,2,1,2,1]], [[4,2,0,3,2,5]], [[0]], [[1,2,3,4]],
            [[4,3,2,1]], [[2,0,2]], [[5,5,5]], [_ints(7, 1800, 0, 1000)],
        ],
        """
        class Solution:
            def trap(self, height):
                left, right = 0, len(height) - 1
                left_max = right_max = 0
                ans = 0
                while left < right:
                    if height[left] < height[right]:
                        left_max = max(left_max, height[left])
                        ans += left_max - height[left]
                        left += 1
                    else:
                        right_max = max(right_max, height[right])
                        ans += right_max - height[right]
                        right -= 1
                return ans
        """,
        "时间 O(n)，空间 O(1)",
        ["题型：双指针。每格水量要看左右最大值，暴力向两边找会 O(n²)。", "较矮一侧的最高边界已经被另一侧保证，能立即确定该侧水量。", "维护 `left_max/right_max`，每次处理高度较小的一端并向内移动。"],
        "谁更矮，就先结算谁，因为另一侧至少能提供边界。",
        ["水量不能为负，必须先更新当前侧最大值", "单调数组应返回 0", "只看相邻柱子会漏掉远处边界"],
    ),
    P(
        "move-zeroes", "移动零", "two_pointers", "easy", 283,
        "给定数组 `nums`，把所有 0 移到末尾，同时保持非零元素的相对顺序。\n\n必须原地修改数组，函数返回 `None`，判题会读取修改后的第 0 个参数。",
        [
            {"input": "nums = [0,1,0,3,12]", "output": "[1,3,12,0,0]", "note": "非零元素顺序不变"},
            {"input": "nums = [0]", "output": "[0]", "note": "单元素直接保留"},
        ],
        ["1 <= len(nums) <= 10^4", "-2^31 <= nums[i] <= 2^31 - 1", "必须原地修改 `nums`"],
        "moveZeroes", [("nums", "List[int]")], "None",
        [
            [[0,1,0,3,12]], [[0]], [[1]], [[0,0,0]], [[1,2,3]], [[0,0,1]], [[1,0,2,0,3]], [_ints(8, 1600, -3, 3)],
        ],
        """
        class Solution:
            def moveZeroes(self, nums):
                write = 0
                for read, x in enumerate(nums):
                    if x != 0:
                        nums[write], nums[read] = nums[read], nums[write]
                        write += 1
                return None
        """,
        "时间 O(n)，空间 O(1)",
        ["题型：双指针原地覆盖。额外数组简单但违背原地要求。", "`write` 指向下一个非零元素应放的位置，`read` 扫描所有元素。", "遇到非零就交换到 `write`，然后 `write += 1`；零自然被挤到后面。"],
        "用慢指针维护非零前缀，扫描时把非零元素稳定搬到前面。",
        ["返回新数组而不改原数组会失败", "交换后忘记推进 `write` 会覆盖非零元素"],
        ret_type="inplace0",
    ),
    P(
        "longest-substring-without-repeating-characters", "无重复字符的最长子串", "sliding_window", "medium", 3,
        "给定字符串 `s`，找出不含重复字符的最长连续子串长度。\n\n子串必须在原字符串中连续，大小写、空格和符号都按不同字符处理。",
        [{"input": "s = 'abcabcbb'", "output": "3", "note": "最长可以是 abc"}, {"input": "s = 'bbbbb'", "output": "1", "note": "只能取一个 b"}],
        ["0 <= len(s) <= 5 * 10^4", "`s` 可包含英文字母、数字、符号和空格", "返回最长连续子串长度"],
        "lengthOfLongestSubstring", [("s", "str")], "int",
        [["abcabcbb"], ["bbbbb"], ["pwwkew"], [""], [" "], ["au"], ["abba"], [_str(9, 2000, "abcdefg")]],
        """
        class Solution:
            def lengthOfLongestSubstring(self, s):
                left = 0
                seen = {}
                ans = 0
                for right, ch in enumerate(s):
                    if ch in seen and seen[ch] >= left:
                        left = seen[ch] + 1
                    seen[ch] = right
                    ans = max(ans, right - left + 1)
                return ans
        """,
        "时间 O(n)，空间 O(min(n,字符集大小))",
        ["题型：滑动窗口。连续子串和“不重复”提示维护一个窗口，暴力枚举子串会重复检查。", "窗口 `[left,right]` 始终保持无重复；若遇到窗口内重复字符，就把左边界跳过旧位置。", "记录每个字符最近位置，右指针逐个进入，更新 `left=max(left,last[ch]+1)` 和答案。"],
        "维护一个始终无重复的窗口，重复时左边界直接跳到旧字符后面。",
        ["`left` 不能往回退，否则 `abba` 会算错", "把子序列当成子串会错，必须连续"],
    ),
    P(
        "find-all-anagrams-in-a-string", "找到字符串中所有字母异位词", "sliding_window", "medium", 438,
        "给定字符串 `s` 和模式串 `p`，找出 `s` 中所有长度等于 `p` 且字符计数相同的子串起点。\n\n返回起点下标列表，下标按从小到大输出。",
        [{"input": "s = 'cbaebabacd', p = 'abc'", "output": "[0,6]", "note": "cba 和 bac 都是 abc 的异位词"}, {"input": "s = 'abab', p = 'ab'", "output": "[0,1,2]", "note": "三个窗口都满足"}],
        ["1 <= len(s), len(p) <= 3 * 10^4", "`s` 和 `p` 只包含小写英文字母", "返回所有合法窗口的起点"],
        "findAnagrams", [("s", "str"), ("p", "str")], "List[int]",
        [["cbaebabacd", "abc"], ["abab", "ab"], ["a", "a"], ["a", "b"], ["baa", "aa"], ["aaaaaaaaaa", "aa"], ["abc", "abcd"], [_str(10, 2000, "abcd"), "abc"]],
        """
        class Solution:
            def findAnagrams(self, s, p):
                need = Counter(p)
                window = Counter()
                ans = []
                m = len(p)
                for right, ch in enumerate(s):
                    window[ch] += 1
                    if right >= m:
                        old = s[right - m]
                        window[old] -= 1
                        if window[old] == 0:
                            del window[old]
                    if right >= m - 1 and window == need:
                        ans.append(right - m + 1)
                return ans
        """,
        "时间 O(n)，空间 O(1)",
        ["题型：固定长度滑动窗口。异位词只关心字符计数，暴力排序每个窗口太慢。", "窗口长度固定为 `len(p)`，维护当前窗口的字符频次。", "右边加入字符；窗口过长就移除最左字符；频次等于 `p` 时记录起点。"],
        "固定窗口长度等于 `p`，比较窗口频次和目标频次。",
        ["窗口缩小时频次变 0 不删除会影响 Counter 比较", "窗口长度没到 `len(p)` 就比较会误报"],
    ),
    P(
        "minimum-window-substring", "最小覆盖子串", "sliding_window", "hard", 76,
        "给定字符串 `s` 和 `t`，在 `s` 中找出包含 `t` 所有字符及其次数的最短连续子串。\n\n如果不存在这样的窗口，返回空字符串；若存在唯一最短答案，返回它。",
        [{"input": "s = 'ADOBECODEBANC', t = 'ABC'", "output": "'BANC'", "note": "BANC 是最短覆盖"}, {"input": "s = 'a', t = 'aa'", "output": "''", "note": "s 中 a 的数量不够"}],
        ["1 <= len(s), len(t) <= 10^5", "`s` 和 `t` 由英文字母组成", "若无覆盖窗口返回空字符串"],
        "minWindow", [("s", "str"), ("t", "str")], "str",
        [["ADOBECODEBANC", "ABC"], ["a", "aa"], ["a", "a"], ["aa", "aa"], ["ab", "b"], ["bba", "ab"], ["abc", "d"], [_str(11, 2500, "abcde") + "XYZ", "XYZ"]],
        """
        class Solution:
            def minWindow(self, s, t):
                need = Counter(t)
                missing = len(t)
                left = start = 0
                best = float('inf')
                for right, ch in enumerate(s):
                    if need[ch] > 0:
                        missing -= 1
                    need[ch] -= 1
                    while missing == 0:
                        if right - left + 1 < best:
                            best = right - left + 1
                            start = left
                        old = s[left]
                        need[old] += 1
                        if need[old] > 0:
                            missing += 1
                        left += 1
                return "" if best == float('inf') else s[start:start + best]
        """,
        "时间 O(n)，空间 O(字符集大小)",
        ["题型：可变滑动窗口。要求最短覆盖，暴力枚举所有子串会 O(n²)。", "右指针扩大直到覆盖 `t`，一旦合法就不断移动左指针尝试变短。", "用 `missing` 表示还缺多少字符；右进减少缺口，左缩导致缺口恢复时停止。"],
        "右扩找可行窗口，合法后左缩到刚好不可再缩。",
        ["只检查字符种类不检查次数会让 `t='aa'` 出错", "更新最短答案必须发生在每次合法窗口左缩前"],
    ),
    P(
        "subarray-sum-equals-k", "和为 K 的子数组", "prefix_sum", "medium", 560,
        "给定整数数组 `nums` 和整数 `k`，统计和恰好为 `k` 的连续子数组个数。\n\n数组中可以有负数，所以不能只靠窗口单调移动。",
        [{"input": "nums = [1,1,1], k = 2", "output": "2", "note": "两个长度为 2 的子数组"}, {"input": "nums = [1,2,3], k = 3", "output": "2", "note": "[1,2] 和 [3]"}],
        ["1 <= len(nums) <= 2 * 10^4", "-1000 <= nums[i] <= 1000", "-10^7 <= k <= 10^7"],
        "subarraySum", [("nums", "List[int]"), ("k", "int")], "int",
        [[[1,1,1], 2], [[1,2,3], 3], [[1], 0], [[0,0,0], 0], [[-1,-1,1], 0], [[3,4,7,2,-3,1,4,2], 7], [[1,-1,1,-1], 0], [_ints(12, 1800, -5, 5), 3]],
        """
        class Solution:
            def subarraySum(self, nums, k):
                cnt = defaultdict(int)
                cnt[0] = 1
                prefix = ans = 0
                for x in nums:
                    prefix += x
                    ans += cnt[prefix - k]
                    cnt[prefix] += 1
                return ans
        """,
        "时间 O(n)，空间 O(n)",
        ["题型：前缀和 + 哈希。连续子数组和可以由两个前缀和相减得到。", "若当前前缀和为 `pre`，需要之前出现过 `pre-k`。", "初始化 `cnt[0]=1`；边累加前缀边把能配成 `k` 的历史次数加入答案。"],
        "子数组和为 k 等价于两个前缀和差为 k。",
        ["忘记 `cnt[0]=1` 会漏掉从下标 0 开始的子数组", "有负数时滑动窗口不适用"],
    ),
    P(
        "product-of-array-except-self", "除自身以外数组的乘积", "prefix_sum", "medium", 238,
        "给定整数数组 `nums`，返回数组 `answer`，其中 `answer[i]` 等于除 `nums[i]` 外所有元素的乘积。\n\n不能使用除法，并要求在线性时间内完成。",
        [{"input": "nums = [1,2,3,4]", "output": "[24,12,8,6]", "note": "每位排除自身后相乘"}, {"input": "nums = [-1,1,0,-3,3]", "output": "[0,0,9,0,0]", "note": "包含一个 0"}],
        ["2 <= len(nums) <= 10^5", "-30 <= nums[i] <= 30", "任意前缀或后缀乘积在 32 位整数范围内", "不能使用除法"],
        "productExceptSelf", [("nums", "List[int]")], "List[int]",
        [[[1,2,3,4]], [[-1,1,0,-3,3]], [[1,2]], [[0,0]], [[2,3,0,4]], [[-1,-2,-3,-4]], [[1]*20], [[(lambda r: [r.choice([-1, 0, 1]) for _ in range(1600)])(random.Random(13))]]],
        """
        class Solution:
            def productExceptSelf(self, nums):
                n = len(nums)
                ans = [1] * n
                left = 1
                for i in range(n):
                    ans[i] = left
                    left *= nums[i]
                right = 1
                for i in range(n - 1, -1, -1):
                    ans[i] *= right
                    right *= nums[i]
                return ans
        """,
        "时间 O(n)，空间 O(1)（不计输出）",
        ["题型：前后缀积。每个位置需要左边所有数和右边所有数的乘积。", "先把左侧乘积写进答案，再从右往左乘上右侧乘积。", "两个滚动变量 `left/right` 就能替代完整前缀、后缀数组。"],
        "答案等于左侧乘积乘右侧乘积，分两趟滚动计算。",
        ["使用除法会在有 0 时出错且不符合要求", "右侧遍历时要先乘 `right` 再更新 `right *= nums[i]`"],
    ),
    P(
        "contiguous-array", "连续数组", "prefix_sum", "medium", 525,
        "给定只含 0 和 1 的数组 `nums`，找出 0 和 1 数量相同的最长连续子数组长度。\n\n可以把 0 看成 -1，这样目标就变成最长和为 0 的子数组。",
        [{"input": "nums = [0,1]", "output": "2", "note": "整个数组平衡"}, {"input": "nums = [0,1,0]", "output": "2", "note": "任意相邻 0,1 可组成长度 2"}],
        ["1 <= len(nums) <= 10^5", "nums[i] 只能是 0 或 1", "返回最长连续长度"],
        "findMaxLength", [("nums", "List[int]")], "int",
        [[[0,1]], [[0,1,0]], [[0]], [[1]], [[0,0,1,1]], [[0,1,1,0,1,1,1,0]], [[0,0,0,1,1,1,0]], [[random.Random(14).randint(0,1) for _ in range(2000)]]],
        """
        class Solution:
            def findMaxLength(self, nums):
                first = {0: -1}
                prefix = ans = 0
                for i, x in enumerate(nums):
                    prefix += 1 if x == 1 else -1
                    if prefix in first:
                        ans = max(ans, i - first[prefix])
                    else:
                        first[prefix] = i
                return ans
        """,
        "时间 O(n)，空间 O(n)",
        ["题型：前缀和。0 和 1 个数相同可以转成 +1/-1 后和为 0。", "相同前缀和之间的区间和为 0，长度越长越好。", "记录每个前缀和第一次出现的位置，后续再次出现时更新最大距离。"],
        "把 0 当 -1，最长平衡区间就是相同前缀和的最大跨度。",
        ["覆盖前缀和第一次出现位置会丢掉最长距离", "忘记初始 `{0:-1}` 会漏掉从头开始的答案"],
    ),
    P(
        "search-insert-position", "搜索插入位置", "binary_search", "easy", 35,
        "给定严格升序数组 `nums` 和目标值 `target`，如果目标存在就返回下标。\n\n如果不存在，返回它按顺序插入后应处的位置。",
        [{"input": "nums = [1,3,5,6], target = 5", "output": "2", "note": "5 已存在"}, {"input": "nums = [1,3,5,6], target = 2", "output": "1", "note": "2 应插在 1 和 3 之间"}],
        ["1 <= len(nums) <= 10^4", "-10^4 <= nums[i], target <= 10^4", "nums 严格递增"],
        "searchInsert", [("nums", "List[int]"), ("target", "int")], "int",
        [[[1,3,5,6], 5], [[1,3,5,6], 2], [[1,3,5,6], 7], [[1,3,5,6], 0], [[1], 1], [[1], 0], [[-10,-3,0,8], -4], [_sorted(15, 1800, -5000, 5000), 123]],
        """
        class Solution:
            def searchInsert(self, nums, target):
                lo, hi = 0, len(nums)
                while lo < hi:
                    mid = (lo + hi) // 2
                    if nums[mid] >= target:
                        hi = mid
                    else:
                        lo = mid + 1
                return lo
        """,
        "时间 O(log n)，空间 O(1)",
        ["题型：二分查找。升序数组和插入位置提示找第一个大于等于目标的位置。", "保持答案在 `[lo,hi)` 中，判断 `nums[mid] >= target` 时收缩右边界。", "循环 `while lo < hi`，结束时 `lo` 就是 lower_bound。"],
        "插入位置就是第一个 `>= target` 的下标。",
        ["用闭区间时边界容易死循环", "目标大于所有元素时应返回 `len(nums)`"],
    ),
    P(
        "find-first-and-last-position-of-element-in-sorted-array", "在排序数组中查找元素的第一个和最后一个位置", "binary_search", "medium", 34,
        "给定非降序数组 `nums` 和 `target`，返回目标值出现的起止下标。\n\n如果目标不存在，返回 `[-1,-1]`，要求使用对数级时间复杂度。",
        [{"input": "nums = [5,7,7,8,8,10], target = 8", "output": "[3,4]", "note": "8 连续出现在下标 3 到 4"}, {"input": "nums = [5,7,7,8,8,10], target = 6", "output": "[-1,-1]", "note": "6 不存在"}],
        ["0 <= len(nums) <= 10^5", "-10^9 <= nums[i], target <= 10^9", "nums 非降序排列", "要求 O(log n)"],
        "searchRange", [("nums", "List[int]"), ("target", "int")], "List[int]",
        [[[5,7,7,8,8,10], 8], [[5,7,7,8,8,10], 6], [[], 0], [[1], 1], [[1], 0], [[2,2,2], 2], [[1,2,3,3,3,4], 3], [sorted(_ints(16, 1800, -30, 30)), 7]],
        """
        class Solution:
            def searchRange(self, nums, target):
                def lower(x):
                    lo, hi = 0, len(nums)
                    while lo < hi:
                        mid = (lo + hi) // 2
                        if nums[mid] >= x:
                            hi = mid
                        else:
                            lo = mid + 1
                    return lo
                left = lower(target)
                right = lower(target + 1) - 1
                if left <= right and right < len(nums) and nums[left] == target:
                    return [left, right]
                return [-1, -1]
        """,
        "时间 O(log n)，空间 O(1)",
        ["题型：二分边界。排序数组中找范围，本质是找左右边界。", "左边界是第一个 `>= target`，右边界是第一个 `> target` 的前一个位置。", "写一个 `lower(x)`，返回 `lower(target)` 与 `lower(target+1)-1` 后再校验是否存在。"],
        "范围查询可以拆成两次 lower_bound。",
        ["目标不存在时不校验会返回错误范围", "空数组要直接得到 `[-1,-1]`"],
    ),
    P(
        "search-in-rotated-sorted-array", "搜索旋转排序数组", "binary_search", "medium", 33,
        "给定原本升序、但在某个位置旋转过的数组 `nums`，数组中没有重复值。\n\n返回 `target` 的下标；如果不存在，返回 -1。",
        [{"input": "nums = [4,5,6,7,0,1,2], target = 0", "output": "4", "note": "0 位于旋转后的右半段"}, {"input": "nums = [4,5,6,7,0,1,2], target = 3", "output": "-1", "note": "3 不存在"}],
        ["1 <= len(nums) <= 5000", "-10^4 <= nums[i], target <= 10^4", "nums 中元素互不相同", "nums 是某个升序数组旋转后的结果"],
        "search", [("nums", "List[int]"), ("target", "int")], "int",
        [[[4,5,6,7,0,1,2], 0], [[4,5,6,7,0,1,2], 3], [[1], 0], [[1], 1], [[3,1], 1], [[5,1,3], 5], [[6,7,8,1,2,3,4,5], 4], [(lambda a: a[700:]+a[:700])(list(range(1800))), 1234]],
        """
        class Solution:
            def search(self, nums, target):
                lo, hi = 0, len(nums) - 1
                while lo <= hi:
                    mid = (lo + hi) // 2
                    if nums[mid] == target:
                        return mid
                    if nums[lo] <= nums[mid]:
                        if nums[lo] <= target < nums[mid]:
                            hi = mid - 1
                        else:
                            lo = mid + 1
                    else:
                        if nums[mid] < target <= nums[hi]:
                            lo = mid + 1
                        else:
                            hi = mid - 1
                return -1
        """,
        "时间 O(log n)，空间 O(1)",
        ["题型：变形二分。旋转后每次至少有一半仍然有序。", "判断左半段或右半段是否有序，再看 `target` 是否落在有序半段范围内。", "若目标在有序半段就保留它，否则丢弃该半段继续二分。"],
        "旋转数组二分的关键是每轮识别哪一半有序。",
        ["没有重复值才能用 `nums[lo] <= nums[mid]` 稳定判断", "范围判断的端点开闭写错会漏掉边界元素"],
    ),
    P(
        "koko-eating-bananas", "爱吃香蕉的珂珂", "binary_search", "medium", 875,
        "给定每堆香蕉数量 `piles` 和小时数 `h`，珂珂每小时选择一堆吃最多 `k` 根。\n\n求能在 `h` 小时内吃完所有香蕉的最小整数速度 `k`。",
        [{"input": "piles = [3,6,7,11], h = 8", "output": "4", "note": "速度 4 刚好可行"}, {"input": "piles = [30,11,23,4,20], h = 5", "output": "30", "note": "只有 5 小时，速度要足够大"}],
        ["1 <= len(piles) <= 10^4", "1 <= piles[i] <= 10^9", "len(piles) <= h <= 10^9", "返回最小可行速度"],
        "minEatingSpeed", [("piles", "List[int]"), ("h", "int")], "int",
        [[[3,6,7,11], 8], [[30,11,23,4,20], 5], [[30,11,23,4,20], 6], [[1], 1], [[1,1,1,1], 4], [[1000000000], 2], [[9,9,9], 9], [[random.Random(17).randint(1, 10**6) for _ in range(1800)], 3000]],
        """
        class Solution:
            def minEatingSpeed(self, piles, h):
                lo, hi = 1, max(piles)
                while lo < hi:
                    mid = (lo + hi) // 2
                    hours = sum((p + mid - 1) // mid for p in piles)
                    if hours <= h:
                        hi = mid
                    else:
                        lo = mid + 1
                return lo
        """,
        "时间 O(n log M)，空间 O(1)",
        ["题型：答案二分。速度越快，用时越少，存在单调可行性。", "判断函数是给定速度 `k` 时总小时数是否 `<= h`。", "在 `[1,max(piles)]` 上找第一个可行速度，用向上取整计算每堆耗时。"],
        "最小速度就是单调可行区间的第一个 True。",
        ["每堆耗时要向上取整，不能用普通除法", "上界应取 `max(piles)`，不是香蕉总数"],
    ),
    P(
        "daily-temperatures", "每日温度", "mono_stack", "medium", 739,
        "给定每天温度 `temperatures`，对每一天计算还要等几天才会遇到更高温度。\n\n如果之后没有更高温，结果位置填 0。",
        [{"input": "temperatures = [73,74,75,71,69,72,76,73]", "output": "[1,1,4,2,1,1,0,0]", "note": "下标 2 要等到 76"}, {"input": "temperatures = [30,40,50,60]", "output": "[1,1,1,0]", "note": "每天后一日更热"}],
        ["1 <= len(temperatures) <= 10^5", "30 <= temperatures[i] <= 100", "无更高温时填 0"],
        "dailyTemperatures", [("temperatures", "List[int]")], "List[int]",
        [[[73,74,75,71,69,72,76,73]], [[30,40,50,60]], [[30,60,90]], [[90,80,70]], [[70]], [[70,70,70]], [[50,40,60,55,70]], [[random.Random(18).randint(30,100) for _ in range(2000)]]],
        """
        class Solution:
            def dailyTemperatures(self, temperatures):
                ans = [0] * len(temperatures)
                stack = []
                for i, t in enumerate(temperatures):
                    while stack and temperatures[stack[-1]] < t:
                        j = stack.pop()
                        ans[j] = i - j
                    stack.append(i)
                return ans
        """,
        "时间 O(n)，空间 O(n)",
        ["题型：单调栈。要找右侧第一个更大值，暴力向右扫描会 O(n²)。", "栈里存还没找到答案的下标，温度保持单调不升。", "当前温度更高时弹出栈顶并填等待天数，最后把当前下标入栈。"],
        "用单调栈保存等待更高温的下标，当前值负责结算更低的过去。",
        ["栈里应存下标而不是温度，否则算不出天数", "相等温度不是更高，不能弹出"],
    ),
    P(
        "next-greater-element-ii", "下一个更大元素 II", "mono_stack", "medium", 503,
        "给定循环数组 `nums`，为每个位置找从它右侧继续绕一圈遇到的第一个更大元素。\n\n如果一整圈都没有更大元素，返回 -1。",
        [{"input": "nums = [1,2,1]", "output": "[2,-1,2]", "note": "最后一个 1 可循环看到 2"}, {"input": "nums = [1,2,3,4,3]", "output": "[2,3,4,-1,4]", "note": "4 没有更大元素"}],
        ["1 <= len(nums) <= 10^4", "-10^9 <= nums[i] <= 10^9", "数组按循环方式查找"],
        "nextGreaterElements", [("nums", "List[int]")], "List[int]",
        [[[1,2,1]], [[1,2,3,4,3]], [[1]], [[5,4,3,2,1]], [[1,1,1]], [[2,1,2,4,3]], [[-1,0,-2]], [_ints(19, 1800, -1000, 1000)]],
        """
        class Solution:
            def nextGreaterElements(self, nums):
                n = len(nums)
                ans = [-1] * n
                stack = []
                for i in range(2 * n):
                    x = nums[i % n]
                    while stack and nums[stack[-1]] < x:
                        ans[stack.pop()] = x
                    if i < n:
                        stack.append(i)
                return ans
        """,
        "时间 O(n)，空间 O(n)",
        ["题型：循环数组 + 单调栈。右侧第一个更大值适合栈，循环可模拟两遍。", "第一遍入栈真实下标，第二遍只用来帮助结算未找到答案的位置。", "遍历 `0..2n-1`，用 `i % n` 取值，当前值大于栈顶对应值时弹出填答案。"],
        "循环数组看两遍，单调栈只在第一遍入栈。",
        ["第二遍继续入栈会造成重复下标", "相等元素不能作为更大元素"],
    ),
    P(
        "largest-rectangle-in-histogram", "柱状图中最大的矩形", "mono_stack", "hard", 84,
        "给定柱状图每根柱子的高度 `heights`，宽度都为 1。\n\n求由连续柱子组成的最大矩形面积。",
        [{"input": "heights = [2,1,5,6,2,3]", "output": "10", "note": "高度 5 和 6 组成宽 2 的矩形"}, {"input": "heights = [2,4]", "output": "4", "note": "取高度 2 宽 2 或高度 4 宽 1"}],
        ["1 <= len(heights) <= 10^5", "0 <= heights[i] <= 10^4", "返回最大矩形面积"],
        "largestRectangleArea", [("heights", "List[int]")], "int",
        [[[2,1,5,6,2,3]], [[2,4]], [[1]], [[0,0]], [[1,2,3,4,5]], [[5,4,3,2,1]], [[2,1,2]], [[random.Random(20).randint(0,1000) for _ in range(1000)]]],
        """
        class Solution:
            def largestRectangleArea(self, heights):
                stack = [-1]
                ans = 0
                for i, h in enumerate(heights + [0]):
                    while stack[-1] != -1 and heights[stack[-1]] > h:
                        height = heights[stack.pop()]
                        width = i - stack[-1] - 1
                        ans = max(ans, height * width)
                    stack.append(i)
                return ans
        """,
        "时间 O(n)，空间 O(n)",
        ["题型：单调栈。每根柱子作为最低高度时，需要快速知道左右第一个更矮位置。", "栈中下标高度递增；遇到更矮柱子时，弹出的柱子右边界就确定了。", "在末尾加 0 哨兵清空栈，弹出时宽度为 `i-stack[-1]-1`。"],
        "单调递增栈在遇到更矮柱时结算被弹柱子的最大宽度。",
        ["宽度少减 1 会把边界矮柱算进去", "忘记末尾哨兵会漏结算递增尾段"],
    ),
    P(
        "kth-largest-element-in-an-array", "数组中的第 K 个最大元素", "heap", "medium", 215,
        "给定整数数组 `nums` 和整数 `k`，返回按从大到小排序后的第 `k` 个元素。\n\n注意找的是排序位置，不是去重后的第 `k` 大。",
        [{"input": "nums = [3,2,1,5,6,4], k = 2", "output": "5", "note": "第二大是 5"}, {"input": "nums = [3,2,3,1,2,4,5,5,6], k = 4", "output": "4", "note": "重复值按出现次数参与排序"}],
        ["1 <= k <= len(nums) <= 10^5", "-10^4 <= nums[i] <= 10^4", "返回排序后的第 k 个元素"],
        "findKthLargest", [("nums", "List[int]"), ("k", "int")], "int",
        [[[3,2,1,5,6,4], 2], [[3,2,3,1,2,4,5,5,6], 4], [[1], 1], [[2,1], 2], [[-1,-1], 2], [[5,5,5], 1], [[7,6,5,4,3,2,1], 5], [_ints(21, 2000, -10000, 10000), 73]],
        """
        class Solution:
            def findKthLargest(self, nums, k):
                heap = []
                for x in nums:
                    heapq.heappush(heap, x)
                    if len(heap) > k:
                        heapq.heappop(heap)
                return heap[0]
        """,
        "时间 O(n log k)，空间 O(k)",
        ["题型：堆。只关心前 k 大，完整排序会做多余工作。", "维护大小为 k 的小顶堆，堆中始终保存目前最大的 k 个数。", "遍历推入元素；堆超过 k 就弹出最小值，最后堆顶就是第 k 大。"],
        "大小为 k 的小顶堆保存当前前 k 大。",
        ["把“第 k 大”误解为去重后的第 k 大会错", "使用大顶堆时弹出次数和符号容易写反"],
    ),
    P(
        "top-k-frequent-elements", "前 K 个高频元素", "heap", "medium", 347,
        "给定整数数组 `nums` 和整数 `k`，返回出现频率最高的 `k` 个元素。\n\n答案顺序不重要，题目保证最终集合唯一。",
        [{"input": "nums = [1,1,1,2,2,3], k = 2", "output": "[1,2]", "note": "1 和 2 的频率最高"}, {"input": "nums = [1], k = 1", "output": "[1]", "note": "只有一个元素"}],
        ["1 <= len(nums) <= 10^5", "-10^4 <= nums[i] <= 10^4", "1 <= k <= 不同元素个数", "答案集合唯一"],
        "topKFrequent", [("nums", "List[int]"), ("k", "int")], "List[int]",
        [[[1,1,1,2,2,3], 2], [[1], 1], [[1,2], 2], [[4,4,4,6,6,7], 1], [[-1,-1,-2,-3,-3,-3], 2], [[5,5,6,6,6,7,7,7,7], 3], [[0]*50 + [1]*30 + [2]*10, 2], _topk_case(22)],
        """
        class Solution:
            def topKFrequent(self, nums, k):
                cnt = Counter(nums)
                return [x for x, _ in heapq.nlargest(k, cnt.items(), key=lambda item: item[1])]
        """,
        "时间 O(n log k)，空间 O(n)",
        ["题型：哈希计数 + 堆。频率最高提示先统计次数，排序全部频率不是必须。", "用 `Counter` 得到每个数字频率，再从频率中选前 k 大。", "可以用大小为 k 的堆或 `heapq.nlargest`，结果顺序无需固定。"],
        "先计数，再按频率选出前 k 个元素。",
        ["返回频率而不是元素会错", "答案顺序不重要，但不能漏掉负数或 0"],
        compare="unordered",
    ),
    P(
        "merge-k-sorted-lists", "合并 K 个升序链表", "heap", "hard", 23,
        "给定 `lists`，其中每个元素是一条升序链表的头节点。\n\n把所有链表合并成一条新的升序链表并返回头节点；空链表可能出现。",
        [{"input": "lists = [[1,4,5],[1,3,4],[2,6]]", "output": "[1,1,2,3,4,4,5,6]", "note": "按值从小到大串联"}, {"input": "lists = []", "output": "[]", "note": "没有链表时返回空"}],
        ["0 <= len(lists) <= 10^4", "0 <= 单条链表长度", "所有链表总节点数 <= 10^4", "每条链表按升序排列"],
        "mergeKLists", [("lists", "List[Optional[ListNode]]")], "Optional[ListNode]",
        [[[[1,4,5],[1,3,4],[2,6]]], [[]], [[[]]], [[[1]]], [[[], [1,2,3]]], [[[-3,-1,2],[-2,4],[0,0,5]]], [[[i for i in range(j, j+20, 3)] for j in range(3)]], [[sorted(_ints(23+i, 120, -1000, 1000)) for i in range(12)]]],
        """
        class Solution:
            def mergeKLists(self, lists):
                heap = []
                for i, node in enumerate(lists):
                    if node:
                        heapq.heappush(heap, (node.val, i, node))
                dummy = cur = ListNode()
                seq = len(lists)
                while heap:
                    _, _, node = heapq.heappop(heap)
                    cur.next = node
                    cur = cur.next
                    if node.next:
                        seq += 1
                        heapq.heappush(heap, (node.next.val, seq, node.next))
                cur.next = None
                return dummy.next
        """,
        "时间 O(N log k)，空间 O(k)",
        ["题型：堆。每条链表都升序，最小头节点决定下一个输出。", "用小顶堆保存每条链表当前头节点，弹出最小后推进该链表。", "堆元素带一个唯一序号，避免节点值相同时 Python 比较 `ListNode`。"],
        "多路归并时，用堆维护各链表当前最小头节点。",
        ["堆里只放节点会在值相等时无法比较", "弹出节点后忘记推入 `node.next` 会丢链表后续部分"],
        types=["ListNode[]"], ret_type="ListNode",
    ),
    P(
        "reverse-linked-list", "反转链表", "linked_list", "easy", 206,
        "给定单链表头节点 `head`，把链表方向整体反转。\n\n返回反转后的新头节点，空链表应返回空。",
        [{"input": "head = [1,2,3,4,5]", "output": "[5,4,3,2,1]", "note": "所有 next 指针反向"}, {"input": "head = []", "output": "[]", "note": "空链表不变"}],
        ["0 <= 链表长度 <= 5000", "-5000 <= Node.val <= 5000", "需要返回新头节点"],
        "reverseList", [("head", "Optional[ListNode]")], "Optional[ListNode]",
        [[[1,2,3,4,5]], [[]], [[1]], [[1,2]], [[-1,0,1]], [[5,5,5]], [[9,8,7,6]], [[i for i in range(1800)]]],
        """
        class Solution:
            def reverseList(self, head):
                prev = None
                cur = head
                while cur:
                    nxt = cur.next
                    cur.next = prev
                    prev = cur
                    cur = nxt
                return prev
        """,
        "时间 O(n)，空间 O(1)",
        ["题型：链表指针操作。目标是反转 `next`，用数组会额外占空间。", "维护 `prev` 为已经反转部分的头，`cur` 为待处理节点。", "循环中先保存 `cur.next`，再令 `cur.next=prev`，最后两个指针一起前进。"],
        "保存后继、反转当前、整体前进三步不能乱。",
        ["不先保存 `next` 会断掉剩余链表", "返回原 `head` 会只得到反转后的尾节点"],
        types=["ListNode"], ret_type="ListNode",
    ),
    P(
        "merge-two-sorted-lists", "合并两个有序链表", "linked_list", "easy", 21,
        "给定两条升序链表 `list1` 和 `list2`，将它们合并成一条升序链表。\n\n可以复用原节点，返回合并后链表的头节点。",
        [{"input": "list1 = [1,2,4], list2 = [1,3,4]", "output": "[1,1,2,3,4,4]", "note": "按升序交替连接"}, {"input": "list1 = [], list2 = []", "output": "[]", "note": "两条空链表返回空"}],
        ["0 <= 链表长度 <= 10^4", "-10^4 <= Node.val <= 10^4", "两条链表均按升序排列"],
        "mergeTwoLists", [("list1", "Optional[ListNode]"), ("list2", "Optional[ListNode]")], "Optional[ListNode]",
        [[[1,2,4], [1,3,4]], [[], []], [[], [0]], [[1], []], [[1,1,1], [1,1]], [[-3,-1,2], [-2,0,4]], [[1,3,5], [2,4,6]], [sorted(_ints(24, 900, -1000, 1000)), sorted(_ints(25, 900, -1000, 1000))]],
        """
        class Solution:
            def mergeTwoLists(self, list1, list2):
                dummy = cur = ListNode()
                while list1 and list2:
                    if list1.val <= list2.val:
                        cur.next = list1
                        list1 = list1.next
                    else:
                        cur.next = list2
                        list2 = list2.next
                    cur = cur.next
                cur.next = list1 or list2
                return dummy.next
        """,
        "时间 O(m+n)，空间 O(1)",
        ["题型：链表归并。两条链表都有序，头节点较小者一定先输出。", "用哑节点简化头节点处理，`cur` 指向合并链表尾部。", "反复接上较小头节点并推进对应链表，最后接上剩余链表。"],
        "两个有序链表归并，谁小接谁。",
        ["没有哑节点时头节点分支容易漏空链表", "循环后忘记连接剩余链表会丢尾部"],
        types=["ListNode", "ListNode"], ret_type="ListNode",
    ),
    P(
        "remove-nth-node-from-end-of-list", "删除链表的倒数第 N 个节点", "linked_list", "medium", 19,
        "给定链表头节点 `head` 和整数 `n`，删除倒数第 `n` 个节点。\n\n返回删除后的链表头节点，`n` 保证合法。",
        [{"input": "head = [1,2,3,4,5], n = 2", "output": "[1,2,3,5]", "note": "删除值为 4 的节点"}, {"input": "head = [1], n = 1", "output": "[]", "note": "删除唯一节点"}],
        ["1 <= 链表长度 <= 10^4", "1 <= n <= 链表长度", "0 <= Node.val <= 10^4"],
        "removeNthFromEnd", [("head", "Optional[ListNode]"), ("n", "int")], "Optional[ListNode]",
        [[[1,2,3,4,5], 2], [[1], 1], [[1,2], 1], [[1,2], 2], [[1,2,3], 3], [[1,2,3], 1], [[9,9,9,9], 2], [[i for i in range(1, 1801)], 900]],
        """
        class Solution:
            def removeNthFromEnd(self, head, n):
                dummy = ListNode(0, head)
                fast = slow = dummy
                for _ in range(n):
                    fast = fast.next
                while fast.next:
                    fast = fast.next
                    slow = slow.next
                slow.next = slow.next.next
                return dummy.next
        """,
        "时间 O(n)，空间 O(1)",
        ["题型：快慢指针。倒数第 n 个需要知道它前面的节点，先算长度会多一趟。", "让 `fast` 先走 n 步，之后 `fast` 和 `slow` 同步前进。", "当 `fast` 到尾节点时，`slow.next` 就是要删除的节点；用哑节点处理删除头节点。"],
        "快指针先领先 n 步，慢指针停在待删节点前一个。",
        ["不用哑节点会在删除头节点时出错", "循环条件若写成 `while fast` 会让 `slow` 多走一步"],
        types=["ListNode", None], ret_type="ListNode",
    ),
    P(
        "maximum-depth-of-binary-tree", "二叉树的最大深度", "tree", "easy", 104,
        "给定二叉树根节点 `root`，返回从根节点到最远叶子节点经过的节点数。\n\n空树深度为 0，只有根节点的树深度为 1。",
        [{"input": "root = [3,9,20,None,None,15,7]", "output": "3", "note": "最长路径为 3 层"}, {"input": "root = []", "output": "0", "note": "空树深度为 0"}],
        ["0 <= 节点数 <= 10^4", "-100 <= Node.val <= 100", "输入按层序数组表示二叉树"],
        "maxDepth", [("root", "Optional[TreeNode]")], "int",
        [[[3,9,20,None,None,15,7]], [[]], [[1]], [[1,None,2]], [[1,2,None,3,None,4]], [[1,2,3,4,5,6,7]], [[0,None,1,None,2,None,3]], [_bst_level(list(range(255)))]],
        """
        class Solution:
            def maxDepth(self, root):
                if not root:
                    return 0
                return 1 + max(self.maxDepth(root.left), self.maxDepth(root.right))
        """,
        "时间 O(n)，空间 O(h)",
        ["题型：二叉树 DFS。深度天然由左右子树深度递推。", "空节点深度为 0，非空节点深度为左右子树最大值加 1。", "递归返回当前子树最大深度，也可以用层序 BFS 逐层计数。"],
        "树的最大深度 = 1 + max(左深度, 右深度)。",
        ["空树应返回 0 不是 1", "只看一侧子树会漏掉另一侧更深路径"],
        types=["TreeNode"],
    ),
    P(
        "binary-tree-level-order-traversal", "二叉树的层序遍历", "tree", "medium", 102,
        "给定二叉树根节点 `root`，按从上到下、从左到右的层序返回节点值。\n\n结果按层分组，每一层是一个列表；空树返回空列表。",
        [{"input": "root = [3,9,20,None,None,15,7]", "output": "[[3],[9,20],[15,7]]", "note": "每层单独输出"}, {"input": "root = []", "output": "[]", "note": "空树无层级"}],
        ["0 <= 节点数 <= 2000", "-1000 <= Node.val <= 1000", "输入为二叉树层序数组"],
        "levelOrder", [("root", "Optional[TreeNode]")], "List[List[int]]",
        [[[3,9,20,None,None,15,7]], [[]], [[1]], [[1,2,3,4,5]], [[1,None,2,3]], [[1,2,None,3,None,4]], [[1,2,3,4,None,None,5]], [_bst_level(list(range(511)))]],
        """
        class Solution:
            def levelOrder(self, root):
                if not root:
                    return []
                ans = []
                q = deque([root])
                while q:
                    level = []
                    for _ in range(len(q)):
                        node = q.popleft()
                        level.append(node.val)
                        if node.left:
                            q.append(node.left)
                        if node.right:
                            q.append(node.right)
                    ans.append(level)
                return ans
        """,
        "时间 O(n)，空间 O(n)",
        ["题型：树的 BFS。要求按层分组，队列最自然。", "队列当前长度就是这一层节点数量，处理完这些节点再进入下一层。", "每层循环 `for _ in range(len(q))`，收集值并把非空左右孩子入队。"],
        "层序遍历用队列，固定每轮队列长度来切层。",
        ["遍历时动态使用 `while q` 不分层会把所有值放到一层", "空树要返回 `[]`"],
        types=["TreeNode"],
    ),
    P(
        "validate-binary-search-tree", "验证二叉搜索树", "tree", "medium", 98,
        "给定二叉树根节点 `root`，判断它是否满足二叉搜索树规则。\n\n每个节点必须严格大于左子树所有值、严格小于右子树所有值，重复值不合法。",
        [{"input": "root = [2,1,3]", "output": "True", "note": "左右子树都满足范围"}, {"input": "root = [5,1,4,None,None,3,6]", "output": "False", "note": "3 位于 5 的右子树却小于 5"}],
        ["1 <= 节点数 <= 10^4", "-2^31 <= Node.val <= 2^31 - 1", "BST 要求严格不等"],
        "isValidBST", [("root", "Optional[TreeNode]")], "bool",
        [[[2,1,3]], [[5,1,4,None,None,3,6]], [[1]], [[2,2,2]], [[5,4,6,None,None,3,7]], [[0,-1]], [[10,5,15,None,None,6,20]], [_bst_level(list(range(1000)))]],
        """
        class Solution:
            def isValidBST(self, root):
                def dfs(node, low, high):
                    if not node:
                        return True
                    if not (low < node.val < high):
                        return False
                    return dfs(node.left, low, node.val) and dfs(node.right, node.val, high)
                return dfs(root, float('-inf'), float('inf'))
        """,
        "时间 O(n)，空间 O(h)",
        ["题型：树 DFS + 范围约束。只比较父子节点会漏掉祖先限制。", "每个节点都有来自祖先的合法开区间 `(low, high)`。", "递归左子树时上界变为当前值，递归右子树时下界变为当前值。"],
        "BST 校验要带着祖先给出的上下界。",
        ["只检查直接左右孩子会让 `[5,1,4,None,None,3,6]` 误判", "重复值必须返回 False"],
        types=["TreeNode"],
    ),
    P(
        "diameter-of-binary-tree", "二叉树的直径", "tree", "easy", 543,
        "给定二叉树根节点 `root`，返回任意两个节点之间最长路径的边数。\n\n这条路径不一定经过根节点，但必须沿父子连接行走。",
        [{"input": "root = [1,2,3,4,5]", "output": "3", "note": "路径 4-2-1-3 长度为 3 条边"}, {"input": "root = [1,2]", "output": "1", "note": "两个节点之间一条边"}],
        ["1 <= 节点数 <= 10^4", "-100 <= Node.val <= 100", "返回路径包含的边数"],
        "diameterOfBinaryTree", [("root", "Optional[TreeNode]")], "int",
        [[[1,2,3,4,5]], [[1,2]], [[1]], [[1,2,3,4,None,None,5]], [[1,None,2,None,3]], [[1,2,None,3,None,4]], [[1,2,3,4,5,6,7]], [_bst_level(list(range(511)))]],
        """
        class Solution:
            def diameterOfBinaryTree(self, root):
                ans = 0
                def depth(node):
                    nonlocal ans
                    if not node:
                        return 0
                    left = depth(node.left)
                    right = depth(node.right)
                    ans = max(ans, left + right)
                    return 1 + max(left, right)
                depth(root)
                return ans
        """,
        "时间 O(n)，空间 O(h)",
        ["题型：树形 DFS。最长路径经过某个节点时等于左深度加右深度。", "递归返回当前子树向下的最大深度，同时用全局答案记录左右拼接最大值。", "每个节点计算 `left=depth(left)`、`right=depth(right)`，用 `left+right` 更新直径。"],
        "每个节点都尝试把左最长链和右最长链拼成直径。",
        ["题目要边数，`left+right` 已经是边数不要再加 1", "只返回根节点的左右深度会漏掉子树内部直径"],
        types=["TreeNode"],
    ),
    P(
        "number-of-islands", "岛屿数量", "graph", "medium", 200,
        "给定由字符串 `'1'` 和 `'0'` 组成的网格 `grid`，`'1'` 表示陆地，`'0'` 表示水。\n\n上下左右相邻的陆地连成一个岛屿，返回岛屿总数。",
        [{"input": "grid = [['1','1','1','1','0'],['1','1','0','1','0'],['1','1','0','0','0'],['0','0','0','0','0']]", "output": "1", "note": "所有陆地连成一个岛"}, {"input": "grid = [['1','1','0','0','0'],['1','1','0','0','0'],['0','0','1','0','0'],['0','0','0','1','1']]", "output": "3", "note": "共有三块连通陆地"}],
        ["1 <= len(grid), len(grid[0]) <= 300", "grid[i][j] 是 '0' 或 '1'", "只按上下左右连通"],
        "numIslands", [("grid", "List[List[str]]")], "int",
        [[[['1','1','1','1','0'],['1','1','0','1','0'],['1','1','0','0','0'],['0','0','0','0','0']]], [[['1','1','0','0','0'],['1','1','0','0','0'],['0','0','1','0','0'],['0','0','0','1','1']]], [[['1']]], [[['0']]], [[['1','0','1']]], [[['1'],['0'],['1']]], [_grid_islands(26, 40, 45)], [_grid_islands(27, 45, 40)]],
        """
        class Solution:
            def numIslands(self, grid):
                m, n = len(grid), len(grid[0])
                ans = 0
                for i in range(m):
                    for j in range(n):
                        if grid[i][j] == '1':
                            ans += 1
                            q = deque([(i, j)])
                            grid[i][j] = '0'
                            while q:
                                x, y = q.popleft()
                                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                                    nx, ny = x + dx, y + dy
                                    if 0 <= nx < m and 0 <= ny < n and grid[nx][ny] == '1':
                                        grid[nx][ny] = '0'
                                        q.append((nx, ny))
                return ans
        """,
        "时间 O(mn)，空间 O(mn)",
        ["题型：网格图搜索。连通块数量要在网格上做 DFS/BFS。", "每遇到一个未访问陆地，就发现一个新岛，并把整块陆地标记为已访问。", "用队列从该格出发扩展上下左右，把访问过的 `'1'` 改成 `'0'`。"],
        "一个未访问陆地触发一次 BFS，就对应一个新岛屿。",
        ["对角线不算连通", "网格元素是字符串 `'1'/'0'`，不是整数 1/0"],
    ),
    P(
        "rotting-oranges", "腐烂的橘子", "graph", "medium", 994,
        "网格 `grid` 中 0 为空格、1 为新鲜橘子、2 为腐烂橘子。\n\n每分钟腐烂橘子会感染上下左右的新鲜橘子，返回全部腐烂所需分钟数；如果无法全部腐烂，返回 -1。",
        [{"input": "grid = [[2,1,1],[1,1,0],[0,1,1]]", "output": "4", "note": "逐层扩散需要 4 分钟"}, {"input": "grid = [[2,1,1],[0,1,1],[1,0,1]]", "output": "-1", "note": "左下角橘子无法被感染"}],
        ["1 <= len(grid), len(grid[0]) <= 100", "grid[i][j] 是 0、1 或 2", "感染只沿上下左右传播"],
        "orangesRotting", [("grid", "List[List[int]]")], "int",
        [[[[2,1,1],[1,1,0],[0,1,1]]], [[[2,1,1],[0,1,1],[1,0,1]]], [[[0,2]]], [[[1]]], [[[2]]], [[[2,1,1],[1,1,1],[0,1,2]]], [[[1,2]]], [_matrix(28, 30, 30, [0,1,1,1,2])]],
        """
        class Solution:
            def orangesRotting(self, grid):
                m, n = len(grid), len(grid[0])
                q = deque()
                fresh = 0
                for i in range(m):
                    for j in range(n):
                        if grid[i][j] == 2:
                            q.append((i, j, 0))
                        elif grid[i][j] == 1:
                            fresh += 1
                minutes = 0
                while q:
                    x, y, minutes = q.popleft()
                    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < m and 0 <= ny < n and grid[nx][ny] == 1:
                            grid[nx][ny] = 2
                            fresh -= 1
                            q.append((nx, ny, minutes + 1))
                return minutes if fresh == 0 else -1
        """,
        "时间 O(mn)，空间 O(mn)",
        ["题型：多源 BFS。所有初始腐烂橘子同时向外扩散。", "队列初始放入全部腐烂橘子，并统计新鲜橘子数量。", "BFS 每感染一个新鲜橘子就减少计数并记录分钟，最后看是否还有新鲜橘子。"],
        "同时扩散的问题，用多源 BFS 按层计时。",
        ["不能逐个腐烂源单独 BFS，否则时间会被重复计算", "没有新鲜橘子时应返回 0"],
    ),
    P(
        "course-schedule", "课程表", "graph", "medium", 207,
        "有 `numCourses` 门课，`prerequisites` 中 `[a,b]` 表示上 `a` 前必须先上 `b`。\n\n判断是否可以完成所有课程；如果依赖中存在环，就无法完成。",
        [{"input": "numCourses = 2, prerequisites = [[1,0]]", "output": "True", "note": "先学 0 再学 1"}, {"input": "numCourses = 2, prerequisites = [[1,0],[0,1]]", "output": "False", "note": "两门课互相依赖成环"}],
        ["1 <= numCourses <= 2000", "0 <= len(prerequisites) <= 5000", "0 <= a,b < numCourses", "依赖对中的课程不同"],
        "canFinish", [("numCourses", "int"), ("prerequisites", "List[List[int]]")], "bool",
        [[2, [[1,0]]], [2, [[1,0],[0,1]]], [1, []], [3, [[1,0],[2,1]]], [3, [[1,0],[1,2],[0,1]]], [4, [[1,0],[2,0],[3,1],[3,2]]], [5, []], [1200, [[i+1, i] for i in range(1199)]]],
        """
        class Solution:
            def canFinish(self, numCourses, prerequisites):
                graph = [[] for _ in range(numCourses)]
                indeg = [0] * numCourses
                for a, b in prerequisites:
                    graph[b].append(a)
                    indeg[a] += 1
                q = deque(i for i, d in enumerate(indeg) if d == 0)
                taken = 0
                while q:
                    x = q.popleft()
                    taken += 1
                    for y in graph[x]:
                        indeg[y] -= 1
                        if indeg[y] == 0:
                            q.append(y)
                return taken == numCourses
        """,
        "时间 O(V+E)，空间 O(V+E)",
        ["题型：拓扑排序。课程先修关系是有向图，无法完成等价于有环。", "入度为 0 的课可以先学，学完后减少后继课程入度。", "把所有入度 0 节点入队，逐个弹出计数；最终学完数量等于课程数才可完成。"],
        "课程依赖能否完成，就是有向图是否能拓扑排序完。",
        ["边方向要从先修课指向后续课", "只从 0 号课程出发会漏掉不连通分量"],
    ),
    P(
        "number-of-provinces", "省份数量", "graph", "medium", 547,
        "给定城市连通矩阵 `isConnected`，如果两个城市直接或间接相连，就属于同一个省份。\n\n返回省份总数，也就是无向图连通块数量。",
        [{"input": "isConnected = [[1,1,0],[1,1,0],[0,0,1]]", "output": "2", "note": "城市 0、1 一组，城市 2 单独一组"}, {"input": "isConnected = [[1,0,0],[0,1,0],[0,0,1]]", "output": "3", "note": "互不连通"}],
        ["1 <= len(isConnected) <= 200", "isConnected 是 n x n 矩阵", "isConnected[i][i] = 1", "矩阵关于主对角线对称"],
        "findCircleNum", [("isConnected", "List[List[int]]")], "int",
        [[[[1,1,0],[1,1,0],[0,0,1]]], [[[1,0,0],[0,1,0],[0,0,1]]], [[[1]]], [[[1,1],[1,1]]], [[[1,0,1],[0,1,0],[1,0,1]]], [[[1,1,0,0],[1,1,0,0],[0,0,1,1],[0,0,1,1]]], [[[1 if i==j or abs(i-j)==1 else 0 for j in range(35)] for i in range(35)]], [[[1 if i//5==j//5 else 0 for j in range(40)] for i in range(40)]]],
        """
        class Solution:
            def findCircleNum(self, isConnected):
                n = len(isConnected)
                seen = [False] * n
                ans = 0
                for i in range(n):
                    if not seen[i]:
                        ans += 1
                        q = deque([i])
                        seen[i] = True
                        while q:
                            x = q.popleft()
                            for y, ok in enumerate(isConnected[x]):
                                if ok and not seen[y]:
                                    seen[y] = True
                                    q.append(y)
                return ans
        """,
        "时间 O(n²)，空间 O(n)",
        ["题型：无向图连通块。矩阵给出了城市之间是否有边。", "从每个未访问城市开始 BFS/DFS，把与它直接或间接相连的城市全部标记。", "每启动一次新的搜索，省份数量加 1。"],
        "省份数就是连通矩阵对应无向图的连通块数。",
        ["只看直接相连会漏掉间接连接", "遍历矩阵时不要跳过未访问的独立城市"],
    ),
    P(
        "subsets", "子集", "backtracking", "medium", 78,
        "给定互不相同的整数数组 `nums`，返回它的所有子集。\n\n子集可以按任意顺序返回，每个元素在一个子集中最多出现一次。",
        [{"input": "nums = [1,2,3]", "output": "[[],[1],[2],[1,2],[3],[1,3],[2,3],[1,2,3]]", "note": "共 2^3 个子集"}, {"input": "nums = [0]", "output": "[[],[0]]", "note": "空集也要包含"}],
        ["1 <= len(nums) <= 10", "-10 <= nums[i] <= 10", "nums 中元素互不相同"],
        "subsets", [("nums", "List[int]")], "List[List[int]]",
        [[[1,2,3]], [[0]], [[1]], [[1,2]], [[-1,0,1]], [[3,2,1]], [[1,2,3,4,5]], [[i for i in range(10)]]],
        """
        class Solution:
            def subsets(self, nums):
                ans = []
                path = []
                def backtrack(start):
                    ans.append(path[:])
                    for i in range(start, len(nums)):
                        path.append(nums[i])
                        backtrack(i + 1)
                        path.pop()
                backtrack(0)
                return ans
        """,
        "时间 O(n 2^n)，空间 O(n)（不计答案）",
        ["题型：回溯。要求所有选择组合，暴力位掩码或回溯都可以。", "每个位置可以选或不选；用 `start` 保证后续只选择右侧元素。", "进入节点先记录当前路径，再枚举下一位选择，递归后撤销。"],
        "子集树的每个节点都是一个答案。",
        ["忘记加入空集会少一个答案", "递归时不推进 `start` 会重复使用元素"],
        compare="unordered_deep",
    ),
    P(
        "permutations", "全排列", "backtracking", "medium", 46,
        "给定互不相同的整数数组 `nums`，返回所有可能的排列。\n\n每个排列都必须包含全部元素，排列之间顺序可以任意返回。",
        [{"input": "nums = [1,2,3]", "output": "[[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]]", "note": "共 3! 种排列"}, {"input": "nums = [0,1]", "output": "[[0,1],[1,0]]", "note": "两个元素交换顺序"}],
        ["1 <= len(nums) <= 6", "-10 <= nums[i] <= 10", "nums 中元素互不相同"],
        "permute", [("nums", "List[int]")], "List[List[int]]",
        [[[1,2,3]], [[0,1]], [[1]], [[1,2]], [[-1,0,1]], [[3,2,1]], [[1,2,3,4]], [[1,2,3,4,5,6]]],
        """
        class Solution:
            def permute(self, nums):
                ans = []
                path = []
                used = [False] * len(nums)
                def backtrack():
                    if len(path) == len(nums):
                        ans.append(path[:])
                        return
                    for i, x in enumerate(nums):
                        if used[i]:
                            continue
                        used[i] = True
                        path.append(x)
                        backtrack()
                        path.pop()
                        used[i] = False
                backtrack()
                return ans
        """,
        "时间 O(n n!)，空间 O(n)（不计答案）",
        ["题型：回溯排列。每个位置要从未使用元素中选择一个。", "`path` 表示当前排列前缀，`used` 标记哪些下标已经放入前缀。", "当路径长度等于 `n` 时记录答案；每次选择后递归，返回时撤销选择。"],
        "排列回溯的状态是当前位置前缀和哪些元素已使用。",
        ["只用 `start` 组合式写法会漏掉不同顺序", "撤销时忘记恢复 `used[i]` 会少答案"],
        compare="unordered",
    ),
    P(
        "combination-sum", "组合总和", "backtracking", "medium", 39,
        "给定无重复正整数数组 `candidates` 和目标值 `target`，找出和为目标的所有组合。\n\n同一个数字可以使用多次，组合内部顺序不重要。",
        [{"input": "candidates = [2,3,6,7], target = 7", "output": "[[2,2,3],[7]]", "note": "2 可以重复使用"}, {"input": "candidates = [2,3,5], target = 8", "output": "[[2,2,2,2],[2,3,3],[3,5]]", "note": "组合不按排列重复"}],
        ["1 <= len(candidates) <= 30", "2 <= candidates[i] <= 40", "candidates 中元素互不相同", "1 <= target <= 40"],
        "combinationSum", [("candidates", "List[int]"), ("target", "int")], "List[List[int]]",
        [[[2,3,6,7], 7], [[2,3,5], 8], [[2], 1], [[2], 2], [[2], 4], [[7,3,2], 18], [[5,10,12], 20], [[2,3,5,7,11,13,17,19], 40]],
        """
        class Solution:
            def combinationSum(self, candidates, target):
                candidates.sort()
                ans = []
                path = []
                def backtrack(start, remain):
                    if remain == 0:
                        ans.append(path[:])
                        return
                    for i in range(start, len(candidates)):
                        x = candidates[i]
                        if x > remain:
                            break
                        path.append(x)
                        backtrack(i, remain - x)
                        path.pop()
                backtrack(0, target)
                return ans
        """,
        "时间 O(S)，空间 O(target/min(candidates))",
        ["题型：回溯组合。可重复使用且不区分顺序，不能按排列枚举。", "用 `start` 控制组合非降序；递归仍传 `i` 表示当前数还能继续用。", "排序后若候选值超过剩余目标，可直接剪枝退出循环。"],
        "可重复组合传 `i`，不可回头保证不生成排列重复。",
        ["递归传 `i+1` 会禁止重复使用当前数字", "不限制起点会把 `[2,3]` 和 `[3,2]` 都输出"],
        compare="unordered_deep",
    ),
    P(
        "generate-parentheses", "括号生成", "backtracking", "medium", 22,
        "给定整数 `n`，生成所有由 `n` 对括号组成且合法的字符串。\n\n合法意味着任意前缀中右括号数量不能超过左括号，最终左右括号数量相等。",
        [{"input": "n = 3", "output": "['((()))','(()())','(())()','()(())','()()()']", "note": "共有 5 种"}, {"input": "n = 1", "output": "['()']", "note": "一对括号只有一种"}],
        ["1 <= n <= 7", "只使用字符 '(' 和 ')'", "返回所有合法括号串"],
        "generateParenthesis", [("n", "int")], "List[str]",
        [[3], [1], [2], [4], [5], [6], [7], [1]],
        """
        class Solution:
            def generateParenthesis(self, n):
                ans = []
                path = []
                def backtrack(left, right):
                    if len(path) == 2 * n:
                        ans.append(''.join(path))
                        return
                    if left < n:
                        path.append('(')
                        backtrack(left + 1, right)
                        path.pop()
                    if right < left:
                        path.append(')')
                        backtrack(left, right + 1)
                        path.pop()
                backtrack(0, 0)
                return ans
        """,
        "时间 O(C_n * n)，空间 O(n)",
        ["题型：回溯构造。每一步选择放左括号或右括号，但要保持前缀合法。", "左括号最多放 `n` 个；右括号只有在数量少于左括号时才能放。", "路径长度到 `2*n` 时记录字符串，递归后撤销最后一个括号。"],
        "括号合法性的核心不变量是 `right <= left <= n`。",
        ["只看最终数量相等会产生 `)(` 这类非法前缀", "右括号条件应是 `right < left`，不是 `right < n`"],
        compare="unordered",
    ),
    P(
        "climbing-stairs", "爬楼梯", "dp", "easy", 70,
        "你要爬到第 `n` 阶楼梯，每次可以爬 1 阶或 2 阶。\n\n返回到达第 `n` 阶共有多少种不同走法。",
        [{"input": "n = 2", "output": "2", "note": "1+1 或 2"}, {"input": "n = 3", "output": "3", "note": "1+1+1、1+2、2+1"}],
        ["1 <= n <= 45", "每次只能走 1 或 2 阶", "答案 fits in 32-bit int"],
        "climbStairs", [("n", "int")], "int",
        [[2], [3], [1], [4], [5], [10], [30], [45]],
        """
        class Solution:
            def climbStairs(self, n):
                a, b = 1, 1
                for _ in range(n):
                    a, b = b, a + b
                return a
        """,
        "时间 O(n)，空间 O(1)",
        ["题型：DP。到第 n 阶的最后一步只能来自 n-1 或 n-2。", "状态 `dp[i]` 表示到第 i 阶的走法数，转移为两种来源相加。", "只依赖前两项，用两个变量滚动即可。"],
        "爬楼梯就是斐波那契：`f(n)=f(n-1)+f(n-2)`。",
        ["把第 0 阶初始化错会影响 `n=1/2`", "递归不加缓存会指数级超时"],
    ),
    P(
        "house-robber", "打家劫舍", "dp", "medium", 198,
        "给定每间房的钱数 `nums`，不能偷相邻两间房。\n\n返回在不触发警报的情况下能偷到的最大金额。",
        [{"input": "nums = [1,2,3,1]", "output": "4", "note": "偷第 0 和第 2 间"}, {"input": "nums = [2,7,9,3,1]", "output": "12", "note": "偷 2、9、1"}],
        ["1 <= len(nums) <= 10^4", "0 <= nums[i] <= 400", "不能选择相邻房屋"],
        "rob", [("nums", "List[int]")], "int",
        [[[1,2,3,1]], [[2,7,9,3,1]], [[0]], [[5]], [[2,1,1,2]], [[10,1,1,10]], [[0,0,0]], [_ints(29, 2000, 0, 400)]],
        """
        class Solution:
            def rob(self, nums):
                prev2 = prev1 = 0
                for x in nums:
                    prev2, prev1 = prev1, max(prev1, prev2 + x)
                return prev1
        """,
        "时间 O(n)，空间 O(1)",
        ["题型：DP。相邻不能同时选，当前房屋只有偷或不偷两种选择。", "`dp[i]` 表示前 i 间的最大金额，转移为不偷当前或偷当前加 `dp[i-2]`。", "用两个变量保存 `dp[i-1]` 与 `dp[i-2]`，逐间滚动更新。"],
        "每间房做选择：偷它就接 `i-2`，不偷就沿用 `i-1`。",
        ["贪心挑局部最大会在 `[2,1,1,2]` 上失败", "空前缀金额应初始化为 0"],
    ),
    P(
        "coin-change", "零钱兑换", "dp", "medium", 322,
        "给定硬币面额 `coins` 和金额 `amount`，每种硬币数量无限。\n\n返回凑成 `amount` 所需的最少硬币数；如果无法凑成，返回 -1。",
        [{"input": "coins = [1,2,5], amount = 11", "output": "3", "note": "5+5+1"}, {"input": "coins = [2], amount = 3", "output": "-1", "note": "无法凑出奇数 3"}],
        ["1 <= len(coins) <= 12", "1 <= coins[i] <= 2^31 - 1", "0 <= amount <= 10^4", "每种硬币可无限使用"],
        "coinChange", [("coins", "List[int]"), ("amount", "int")], "int",
        [[[1,2,5], 11], [[2], 3], [[1], 0], [[1], 2], [[2,5,10,1], 27], [[186,419,83,408], 6249], [[3,7,405,436], 8839], [[1,3,4], 9999]],
        """
        class Solution:
            def coinChange(self, coins, amount):
                inf = amount + 1
                dp = [0] + [inf] * amount
                for x in range(1, amount + 1):
                    for c in coins:
                        if c <= x:
                            dp[x] = min(dp[x], dp[x - c] + 1)
                return -1 if dp[amount] == inf else dp[amount]
        """,
        "时间 O(amount * len(coins))，空间 O(amount)",
        ["题型：完全背包 DP。金额可由更小金额加一枚硬币得到。", "状态 `dp[x]` 表示凑成金额 x 的最少硬币数，不可达设为无穷大。", "对每个金额枚举最后一枚硬币 `c`，用 `dp[x-c]+1` 更新。"],
        "最少硬币数来自“最后一枚硬币”之前的最优子问题。",
        ["不可达状态不能当作 0 使用", "`amount=0` 应返回 0"],
    ),
    P(
        "longest-increasing-subsequence", "最长递增子序列", "dp", "medium", 300,
        "给定整数数组 `nums`，求最长严格递增子序列的长度。\n\n子序列不要求连续，但必须保持原有相对顺序。",
        [{"input": "nums = [10,9,2,5,3,7,101,18]", "output": "4", "note": "例如 2,3,7,101"}, {"input": "nums = [0,1,0,3,2,3]", "output": "4", "note": "0,1,2,3"}],
        ["1 <= len(nums) <= 2500", "-10^4 <= nums[i] <= 10^4", "严格递增，不能相等"],
        "lengthOfLIS", [("nums", "List[int]")], "int",
        [[[10,9,2,5,3,7,101,18]], [[0,1,0,3,2,3]], [[7,7,7,7]], [[1]], [[1,2,3,4]], [[4,3,2,1]], [[-1,3,4,-2,0,6,2,3]], [_ints(30, 2000, -10000, 10000)]],
        """
        class Solution:
            def lengthOfLIS(self, nums):
                tails = []
                for x in nums:
                    i = bisect.bisect_left(tails, x)
                    if i == len(tails):
                        tails.append(x)
                    else:
                        tails[i] = x
                return len(tails)
        """,
        "时间 O(n log n)，空间 O(n)",
        ["题型：DP + 二分优化。朴素 DP 要比较前面所有元素，O(n²) 较慢。", "`tails[i]` 表示长度为 i+1 的递增子序列能拥有的最小结尾值。", "对每个数用二分找第一个 `>= x` 的位置替换；若不存在就扩展长度。"],
        "维护每种长度的最小可能结尾，结尾越小越有潜力。",
        ["严格递增要用 `bisect_left`，用 `bisect_right` 会把相等值算进去", "`tails` 不是实际子序列，只用于长度"],
    ),
    P(
        "longest-common-subsequence", "最长公共子序列", "dp", "medium", 1143,
        "给定两个字符串 `text1` 和 `text2`，求它们最长公共子序列长度。\n\n子序列可以删除若干字符但不能改变剩余字符的相对顺序。",
        [{"input": "text1 = 'abcde', text2 = 'ace'", "output": "3", "note": "ace 是公共子序列"}, {"input": "text1 = 'abc', text2 = 'def'", "output": "0", "note": "没有公共字符"}],
        ["1 <= len(text1), len(text2) <= 1000", "字符串只包含小写英文字母", "返回长度而不是具体序列"],
        "longestCommonSubsequence", [("text1", "str"), ("text2", "str")], "int",
        [["abcde", "ace"], ["abc", "def"], ["abc", "abc"], ["a", "a"], ["a", "b"], ["bsbininm", "jmjkbkjkv"], ["aaaa", "aa"], [_str(31, 700, "abcde"), _str(32, 650, "abcde")]],
        """
        class Solution:
            def longestCommonSubsequence(self, text1, text2):
                n = len(text2)
                dp = [0] * (n + 1)
                for a in text1:
                    prev = 0
                    for j, b in enumerate(text2, 1):
                        old = dp[j]
                        if a == b:
                            dp[j] = prev + 1
                        else:
                            dp[j] = max(dp[j], dp[j - 1])
                        prev = old
                return dp[n]
        """,
        "时间 O(mn)，空间 O(n)",
        ["题型：二维 DP。两个序列匹配，状态通常表示两个前缀的答案。", "若当前字符相等，答案来自左上角加 1；否则来自删掉其中一边字符的最大值。", "可用一维数组滚动，`prev` 保存上一行左上角值。"],
        "LCS 看两个前缀：相等走左上加一，不等取上/左最大。",
        ["公共子序列不要求连续，不要写成公共子串", "一维滚动时要先保存旧的 `dp[j]` 作为下一格左上角"],
    ),
    P(
        "edit-distance", "编辑距离", "dp", "medium", 72,
        "给定两个单词 `word1` 和 `word2`，每次可以插入、删除或替换一个字符。\n\n返回把 `word1` 转换成 `word2` 所需的最少操作数。",
        [{"input": "word1 = 'horse', word2 = 'ros'", "output": "3", "note": "horse -> rorse -> rose -> ros"}, {"input": "word1 = 'intention', word2 = 'execution'", "output": "5", "note": "经典编辑距离样例"}],
        ["0 <= len(word1), len(word2) <= 500", "word1 和 word2 由小写英文字母组成", "允许插入、删除、替换三种操作"],
        "minDistance", [("word1", "str"), ("word2", "str")], "int",
        [["horse", "ros"], ["intention", "execution"], ["", ""], ["", "abc"], ["abc", ""], ["abc", "abc"], ["kitten", "sitting"], [_str(33, 450, "abcd"), _str(34, 420, "abcd")]],
        """
        class Solution:
            def minDistance(self, word1, word2):
                n = len(word2)
                dp = list(range(n + 1))
                for i, a in enumerate(word1, 1):
                    prev = dp[0]
                    dp[0] = i
                    for j, b in enumerate(word2, 1):
                        old = dp[j]
                        if a == b:
                            dp[j] = prev
                        else:
                            dp[j] = 1 + min(prev, dp[j], dp[j - 1])
                        prev = old
                return dp[n]
        """,
        "时间 O(mn)，空间 O(n)",
        ["题型：二维 DP。编辑两个字符串时，状态是两个前缀之间的最小代价。", "字符相等不用操作；不等时从替换、删除、插入三种操作取最小。", "初始化空串到前缀的代价；一维滚动时 `prev` 表示左上角状态。"],
        "编辑距离的三种操作分别对应左上、上、左三个状态。",
        ["空字符串初始化不正确会让边界用例失败", "替换、插入、删除三个方向少考虑一个会低估或高估答案"],
    ),
    P(
        "merge-intervals", "合并区间", "greedy", "medium", 56,
        "给定若干闭区间 `intervals`，把所有有重叠的区间合并。\n\n返回合并后的区间列表；输出顺序不作为重点，但每个区间应表示合并后的范围。",
        [{"input": "intervals = [[1,3],[2,6],[8,10],[15,18]]", "output": "[[1,6],[8,10],[15,18]]", "note": "[1,3] 和 [2,6] 重叠"}, {"input": "intervals = [[1,4],[4,5]]", "output": "[[1,5]]", "note": "端点相接也算重叠"}],
        ["1 <= len(intervals) <= 10^4", "intervals[i].length == 2", "0 <= start <= end <= 10^4"],
        "merge", [("intervals", "List[List[int]]")], "List[List[int]]",
        [[[[1,3],[2,6],[8,10],[15,18]]], [[[1,4],[4,5]]], [[[1,4],[0,0]]], [[[1,4]]], [[[1,4],[2,3]]], [[[1,2],[3,4],[5,6]]], [[[5,7],[1,3],[2,6]]], [_intervals(36, 1000)]],
        """
        class Solution:
            def merge(self, intervals):
                intervals.sort(key=lambda x: x[0])
                ans = []
                for start, end in intervals:
                    if not ans or ans[-1][1] < start:
                        ans.append([start, end])
                    else:
                        ans[-1][1] = max(ans[-1][1], end)
                return ans
        """,
        "时间 O(n log n)，空间 O(n)",
        ["题型：排序 + 贪心。区间重叠关系在按起点排序后最容易判断。", "维护已经合并结果的最后一个区间；当前起点若不超过其终点，就可以合并。", "排序后依次扫描，不重叠就追加，重叠就更新最后区间右端点。"],
        "按起点排序后，只需和结果中的最后一个区间比较。",
        ["端点相等 `[1,4]` 与 `[4,5]` 要合并", "不排序会漏掉前后交错的重叠区间"],
        compare="unordered",
    ),
    P(
        "jump-game", "跳跃游戏", "greedy", "medium", 55,
        "给定非负整数数组 `nums`，`nums[i]` 表示从位置 `i` 最远能跳多远。\n\n判断是否可以从下标 0 到达最后一个下标。",
        [{"input": "nums = [2,3,1,1,4]", "output": "True", "note": "可以从 0 跳到 1 再跳到终点"}, {"input": "nums = [3,2,1,0,4]", "output": "False", "note": "会被下标 3 的 0 卡住"}],
        ["1 <= len(nums) <= 10^4", "0 <= nums[i] <= 10^5", "只需判断能否到达末尾"],
        "canJump", [("nums", "List[int]")], "bool",
        [[[2,3,1,1,4]], [[3,2,1,0,4]], [[0]], [[1,0]], [[0,1]], [[2,0,0]], [[1,1,1,1]], [_jumps(37, 2000)]],
        """
        class Solution:
            def canJump(self, nums):
                far = 0
                for i, jump in enumerate(nums):
                    if i > far:
                        return False
                    far = max(far, i + jump)
                    if far >= len(nums) - 1:
                        return True
                return True
        """,
        "时间 O(n)，空间 O(1)",
        ["题型：贪心。每个位置只需要关心当前能到达的最远边界。", "遍历到的位置必须不超过 `far`；否则当前位置不可达。", "每到一个可达位置，就用 `i + nums[i]` 更新最远可达下标。"],
        "维护目前能到的最远位置，任何超过它的下标都不可达。",
        ["看到 0 就直接返回 False 会误判 `[2,0,0]`", "没有先判断 `i > far` 就更新会让不可达位置贡献跳跃能力"],
    ),
    P(
        "non-overlapping-intervals", "无重叠区间", "greedy", "medium", 435,
        "给定若干区间 `intervals`，每次可以移除一个区间。\n\n返回为了让剩余区间互不重叠，最少需要移除多少个区间；端点相等不算重叠。",
        [{"input": "intervals = [[1,2],[2,3],[3,4],[1,3]]", "output": "1", "note": "移除 [1,3] 即可"}, {"input": "intervals = [[1,2],[1,2],[1,2]]", "output": "2", "note": "只能保留一个"}],
        ["1 <= len(intervals) <= 10^5", "intervals[i].length == 2", "-5 * 10^4 <= start < end <= 5 * 10^4", "端点相接不重叠"],
        "eraseOverlapIntervals", [("intervals", "List[List[int]]")], "int",
        [[[[1,2],[2,3],[3,4],[1,3]]], [[[1,2],[1,2],[1,2]]], [[[1,2],[2,3]]], [[[1,100],[11,22],[1,11],[2,12]]], [[[1,3],[2,4],[3,5]]], [[[1,2]]], [[[-3,-1],[-2,0],[0,2]]], [_erase_intervals(38, 850)]],
        """
        class Solution:
            def eraseOverlapIntervals(self, intervals):
                intervals.sort(key=lambda x: x[1])
                keep = 0
                end = -float('inf')
                for start, finish in intervals:
                    if start >= end:
                        keep += 1
                        end = finish
                return len(intervals) - keep
        """,
        "时间 O(n log n)，空间 O(1)（排序除外）",
        ["题型：贪心区间调度。最少移除等价于最多保留互不重叠区间。", "为了给后面留下最大空间，每次选择结束最早且不冲突的区间。", "按右端点排序，若当前起点 `>= end` 就保留并更新 `end`，否则移除它。"],
        "最多保留不重叠区间时，优先保留结束最早的。",
        ["按起点排序再随意删除会在嵌套区间上失败", "端点相等不重叠，判断应为 `start >= end`"],
    ),
]
