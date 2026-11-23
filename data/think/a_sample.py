# 思路阶梯样板（由主会话手写，worker 照这个密度和口吻写其余题目）
LADDERS = {
    "longest-substring-without-repeating-characters": dict(
        read="在字符串里找一段连续、并且里面没有重复字符的子串，返回它最长能有多长。",
        steps=[
            dict(k="ask", q="题目最终要你输出什么？",
                 options=["一个数：满足条件的最长长度（最值）", "所有满足条件的子串（列举方案）", "是否存在满足条件的子串（真假）", "满足条件的子串有多少个（计数）"],
                 answer=0,
                 why="“最长……的长度”是求最值。最值类不需要把方案都列出来，只要在扫描过程中维护一个当前最好值 ans，这就排除了回溯这类“列举所有方案”的方法。"),
            dict(k="input", q="题面里哪句话是题眼？",
                 options=["“连续的子串” + “不含重复字符”", "“字符串只含小写字母”", "“返回长度而不是子串本身”"],
                 answer=0,
                 why="“连续子串 / 子数组 + 最长 / 最短 + 满足某个条件”是滑动窗口的标准信号：答案一定是原串里的一段区间 [left, right]，可以用两个下标描述。"),
            dict(k="brute", q="不管效率，最笨的写法是什么？复杂度多少？",
                 options=["枚举每个起点 i，从 i 往右扩，遇到重复就停，记录最长：O(n²)", "先排序再去重：O(n log n)", "枚举所有子序列再判断：O(2ⁿ)"],
                 answer=0,
                 why="面试卡住时先写这个保底：外层固定起点，内层用 set 记出现过的字符往右走，撞到重复就 break。它能过小数据，也是后面优化的出发点。排序会打乱“连续”，子序列不是子串，都偏了。"),
            dict(k="waste", q="暴力解哪里在做重复功？",
                 options=["起点右移一格后，内层又从头扫，前面已经确认无重复的那段被重复检查", "set 的查找太慢", "每次都要重新计算字符串长度"],
                 answer=0,
                 why="起点从 i 挪到 i+1 时，[i+1, 上次停下的位置) 这一段我们早就知道没有重复，内层却从 i+1 重新扫一遍。浪费在于：右端点被“退回去”了。只要右端点永远不回退，就能从 O(n²) 降到 O(n)。"),
            dict(k="tool", q="所以换成什么方法 + 什么数据结构？",
                 options=["滑动窗口（左右双指针都只往右走）+ 哈希表记每个字符最近出现的位置", "单调栈记录字符", "动态规划 dp[i][j] 表示 s[i..j] 是否无重复"],
                 answer=0,
                 why="右指针每步把一个新字符放进窗口；如果它在窗口里已经出现过，左指针直接跳到“旧位置 + 1”。要 O(1) 知道“这个字符上次在哪”，就用 dict：字符 → 最近下标。二维 dp 是 O(n²) 空间，没必要。"),
            dict(k="state", q="窗口必须时刻保持的不变量是什么？",
                 options=["窗口 [left, right] 内没有重复字符，且 left 只增不减", "窗口长度固定为 k", "窗口内字符按字典序递增"],
                 answer=0,
                 why="不变量就是写代码的“合同”：每轮循环结束时窗口里没有重复，所以 right - left + 1 就是一个合法长度，可以拿来更新 ans。left 只增不减是 abba 这类用例的关键：旧位置在窗口左边时不能把 left 往回拉。"),
        ],
        brute="""class Solution:
    def lengthOfLongestSubstring(self, s):
        ans = 0
        for i in range(len(s)):
            seen = set()
            for j in range(i, len(s)):
                if s[j] in seen:
                    break
                seen.add(s[j])
            ans = max(ans, len(seen))
        return ans
""",
        cloze=dict(
            code="""class Solution:
    def lengthOfLongestSubstring(self, s):
        last = {}            # 字符 -> 最近一次出现的下标
        left = ans = 0
        for right, ch in enumerate(s):
            if ch in last and ⟦1⟧:
                left = ⟦2⟧
            last[ch] = right
            ans = ⟦3⟧
        return ans
""",
            blanks=[
                dict(a="last[ch] >= left", hint="旧位置要还在窗口里才需要移动左边界（想想 abba）"),
                dict(a="last[ch] + 1", hint="左边界跳到旧位置的下一格"),
                dict(a="max(ans, right - left + 1)", hint="当前窗口长度 = 右 - 左 + 1"),
            ],
        ),
        say="这题是求连续子串的最长长度，信号是“连续 + 最长 + 满足条件”，用滑动窗口。我维护一个窗口 [left, right]，保证里面没有重复字符，再用一个哈希表记每个字符最近出现的下标。右指针每走一步，如果当前字符的旧位置还在窗口里，就把 left 跳到旧位置加一，然后用窗口长度更新答案。两个指针都只往右走，时间 O(n)，空间是字符集大小。",
        trap="left 不能往回退：abba 走到最后一个 a 时，a 的旧位置 0 已经在窗口左边，不能把 left 拉回 1。要么判断 last[ch] >= left，要么写成 left = max(left, last[ch] + 1)。",
    ),
}
