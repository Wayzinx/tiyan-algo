from textwrap import dedent

def _code(s):
    return dedent(s).strip() + "\n"

ORACLES = {
    'two-sum': dict(
        brute=_code('class Solution:\n    def twoSum(self, nums, target):\n        n = len(nums)\n        for i in range(n):\n            for j in range(i + 1, n):\n                if nums[i] + nums[j] == target:\n                    return [i, j]\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(2, 18)\n    nums = []\n    used = set()\n    while len(nums) < n:\n        x = rng.randint(-40, 40)\n        if x not in used:\n            used.add(x); nums.append(x)\n    i, j = rng.sample(range(n), 2)\n    target = nums[i] + nums[j]\n    for a in range(n):\n        for b in range(a + 1, n):\n            if (a, b) != tuple(sorted((i, j))) and nums[a] + nums[b] == target:\n                return gen_small(rng)\n    return [nums, target]\n'),
        gen_large=_code('def gen_large(rng):\n    nums = [i * 2 for i in range(120000)]\n    nums[-2] = 240001\n    nums[-1] = 240003\n    return [nums, 480004]\n'),
    ),
    'group-anagrams': dict(
        brute=_code('class Solution:\n    def groupAnagrams(self, strs):\n        unused = [False] * len(strs)\n        ans = []\n        for i, s in enumerate(strs):\n            if unused[i]:\n                continue\n            group = [s]\n            unused[i] = True\n            for j in range(i + 1, len(strs)):\n                if not unused[j] and sorted(strs[j]) == sorted(s):\n                    unused[j] = True\n                    group.append(strs[j])\n            ans.append(group)\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    alphabet = "abcd"\n    strs = []\n    for _ in range(rng.randint(1, 18)):\n        k = rng.randint(0, 6)\n        s = "".join(rng.choice(alphabet) for _ in range(k))\n        if rng.random() < 0.35:\n            chars = list(s); rng.shuffle(chars); s = "".join(chars)\n        strs.append(s)\n    return [strs]\n'),
        gen_large=_code('def gen_large(rng):\n    out = []\n    base = "abcdefghij"\n    for i in range(35000):\n        out.append(base[i % 10:] + base[:i % 10])\n    return [out]\n'),
    ),
    'longest-consecutive-sequence': dict(
        brute=_code('class Solution:\n    def longestConsecutive(self, nums):\n        vals = sorted(set(nums))\n        best = cur = 0\n        prev = None\n        for x in vals:\n            if prev is not None and x == prev + 1:\n                cur += 1\n            else:\n                cur = 1\n            best = max(best, cur)\n            prev = x\n        return best\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(0, 25)\n    nums = [rng.randint(-15, 15) for _ in range(n)]\n    if rng.random() < 0.5:\n        start = rng.randint(-20, 5)\n        nums += list(range(start, start + rng.randint(0, 8)))\n        rng.shuffle(nums)\n    return [nums]\n'),
        gen_large=_code('def gen_large(rng):\n    nums = list(range(160000)) + [rng.randint(-1000000, 1000000) for _ in range(30000)]\n    rng.shuffle(nums)\n    return [nums]\n'),
    ),
    'container-with-most-water': dict(
        brute=_code('class Solution:\n    def maxArea(self, height):\n        best = 0\n        for i in range(len(height)):\n            for j in range(i + 1, len(height)):\n                best = max(best, min(height[i], height[j]) * (j - i))\n        return best\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(0, 20) for _ in range(rng.randint(2, 35))]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[rng.randint(0, 10000) for _ in range(250000)]]\n'),
    ),
    '3sum': dict(
        brute=_code('class Solution:\n    def threeSum(self, nums):\n        found = set()\n        n = len(nums)\n        for i in range(n):\n            for j in range(i + 1, n):\n                for k in range(j + 1, n):\n                    if nums[i] + nums[j] + nums[k] == 0:\n                        found.add(tuple(sorted((nums[i], nums[j], nums[k]))))\n        return [list(x) for x in found]\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(-10, 10) for _ in range(rng.randint(0, 16))]]\n'),
        gen_large=_code('def gen_large(rng):\n    nums = [rng.randint(-100000, 100000) for _ in range(1400)]\n    return [nums]\n'),
    ),
    'trapping-rain-water': dict(
        brute=_code('class Solution:\n    def trap(self, height):\n        water = 0\n        for i, h in enumerate(height):\n            left = max(height[:i + 1]) if i >= 0 else 0\n            right = max(height[i:]) if i < len(height) else 0\n            water += max(0, min(left, right) - h)\n        return water\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(0, 12) for _ in range(rng.randint(0, 35))]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[rng.randint(0, 10000) for _ in range(250000)]]\n'),
    ),
    'move-zeroes': dict(
        brute=_code('class Solution:\n    def moveZeroes(self, nums):\n        nonzero = []\n        zeros = 0\n        for x in nums:\n            if x == 0:\n                zeros += 1\n            else:\n                nonzero.append(x)\n        nums[:] = nonzero + [0] * zeros\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.choice([0, 0, 1, -1, 2, rng.randint(-5, 5)]) for _ in range(rng.randint(0, 30))]]\n'),
    ),
    'longest-substring-without-repeating-characters': dict(
        brute=_code('class Solution:\n    def lengthOfLongestSubstring(self, s):\n        best = 0\n        for i in range(len(s) + 1):\n            seen = set()\n            for j in range(i, len(s)):\n                if s[j] in seen:\n                    break\n                seen.add(s[j])\n                best = max(best, j - i + 1)\n        return best\n'),
        gen_small=_code('def gen_small(rng):\n    alphabet = "abcde"\n    return ["".join(rng.choice(alphabet) for _ in range(rng.randint(0, 30)))]\n'),
        gen_large=_code("def gen_large(rng):\n    alphabet = ''.join(chr(33 + i) for i in range(80))\n    return [''.join(rng.choice(alphabet) for _ in range(250000))]\n"),
    ),
    'find-all-anagrams-in-a-string': dict(
        brute=_code('class Solution:\n    def findAnagrams(self, s, p):\n        target = sorted(p)\n        m = len(p)\n        ans = []\n        for i in range(0, len(s) - m + 1):\n            if sorted(s[i:i + m]) == target:\n                ans.append(i)\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    alphabet = "abcd"\n    m = rng.randint(1, 6)\n    n = rng.randint(m, 35)\n    return ["".join(rng.choice(alphabet) for _ in range(n)), "".join(rng.choice(alphabet) for _ in range(m))]\n'),
        gen_large=_code("def gen_large(rng):\n    s = ''.join(rng.choice('abcd') for _ in range(250000))\n    return [s, 'abcda']\n"),
    ),
    'minimum-window-substring': dict(
        brute=_code('class Solution:\n    def minWindow(self, s, t):\n        if not t:\n            return ""\n        need = {}\n        for ch in t:\n            need[ch] = need.get(ch, 0) + 1\n        best = None\n        for i in range(len(s)):\n            have = {}\n            for j in range(i, len(s)):\n                ch = s[j]\n                have[ch] = have.get(ch, 0) + 1\n                ok = True\n                for c, cnt in need.items():\n                    if have.get(c, 0) < cnt:\n                        ok = False; break\n                if ok:\n                    cand = s[i:j + 1]\n                    if best is None or len(cand) < len(best):\n                        best = cand\n                    break\n        return best or ""\n'),
        gen_small=_code('def gen_small(rng):\n    alphabet = "abcde"\n    n = rng.randint(1, 35)\n    s = "".join(rng.choice(alphabet) for _ in range(n))\n    if rng.random() < 0.75:\n        t = "".join(rng.choice(s) for _ in range(rng.randint(1, min(5, len(s)))))\n    else:\n        t = "".join(rng.choice(alphabet + "z") for _ in range(rng.randint(1, 5)))\n    return [s, t]\n'),
        gen_large=_code("def gen_large(rng):\n    s = ''.join(rng.choice('abcde') for _ in range(250000)) + 'XYZ'\n    return [s, 'XYZ']\n"),
    ),
    'subarray-sum-equals-k': dict(
        brute=_code('class Solution:\n    def subarraySum(self, nums, k):\n        ans = 0\n        for i in range(len(nums)):\n            total = 0\n            for j in range(i, len(nums)):\n                total += nums[j]\n                if total == k:\n                    ans += 1\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(-5, 5) for _ in range(rng.randint(0, 30))], rng.randint(-8, 8)]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[rng.randint(-10, 10) for _ in range(250000)], rng.randint(-30, 30)]\n'),
    ),
    'product-of-array-except-self': dict(
        brute=_code('class Solution:\n    def productExceptSelf(self, nums):\n        ans = []\n        for i in range(len(nums)):\n            prod = 1\n            for j, x in enumerate(nums):\n                if i != j:\n                    prod *= x\n            ans.append(prod)\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(-5, 5) for _ in range(rng.randint(2, 14))]]\n'),
        gen_large=_code('def gen_large(rng):\n    nums = [0] * 300000\n    for i in range(0, len(nums), 10000):\n        nums[i] = rng.randint(1, 9)\n    return [nums]\n'),
    ),
    'contiguous-array': dict(
        brute=_code('class Solution:\n    def findMaxLength(self, nums):\n        best = 0\n        for i in range(len(nums)):\n            zeros = ones = 0\n            for j in range(i, len(nums)):\n                if nums[j] == 0: zeros += 1\n                else: ones += 1\n                if zeros == ones:\n                    best = max(best, j - i + 1)\n        return best\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(0, 1) for _ in range(rng.randint(0, 32))]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[rng.randint(0, 1) for _ in range(250000)]]\n'),
    ),
    'search-insert-position': dict(
        brute=_code('class Solution:\n    def searchInsert(self, nums, target):\n        for i, x in enumerate(nums):\n            if x >= target:\n                return i\n        return len(nums)\n'),
        gen_small=_code('def gen_small(rng):\n    nums = sorted(set(rng.randint(-30, 30) for _ in range(rng.randint(1, 25))))\n    return [nums, rng.randint(-35, 35)]\n'),
        gen_large=_code('def gen_large(rng):\n    return [list(range(400000)), 399999]\n'),
    ),
    'find-first-and-last-position-of-element-in-sorted-array': dict(
        brute=_code('class Solution:\n    def searchRange(self, nums, target):\n        first = last = -1\n        for i, x in enumerate(nums):\n            if x == target:\n                if first == -1: first = i\n                last = i\n        return [first, last]\n'),
        gen_small=_code('def gen_small(rng):\n    nums = sorted(rng.randint(-8, 8) for _ in range(rng.randint(0, 35)))\n    return [nums, rng.randint(-10, 10)]\n'),
        gen_large=_code('def gen_large(rng):\n    nums = sorted(rng.randint(0, 100000) for _ in range(400000))\n    return [nums, nums[len(nums)//2]]\n'),
    ),
    'search-in-rotated-sorted-array': dict(
        brute=_code('class Solution:\n    def search(self, nums, target):\n        for i, x in enumerate(nums):\n            if x == target:\n                return i\n        return -1\n'),
        gen_small=_code('def gen_small(rng):\n    vals = sorted(set(rng.randint(-40, 40) for _ in range(rng.randint(1, 25))))\n    k = rng.randrange(len(vals))\n    nums = vals[k:] + vals[:k]\n    target = rng.choice(vals + [rng.randint(41, 60), rng.randint(-60, -41)])\n    return [nums, target]\n'),
        gen_large=_code('def gen_large(rng):\n    vals = list(range(400000))\n    k = 145678\n    return [vals[k:] + vals[:k], 387654]\n'),
    ),
    'koko-eating-bananas': dict(
        brute=_code('class Solution:\n    def minEatingSpeed(self, piles, h):\n        speed = 1\n        while True:\n            hours = 0\n            for p in piles:\n                hours += (p + speed - 1) // speed\n            if hours <= h:\n                return speed\n            speed += 1\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(1, 9)\n    piles = [rng.randint(1, 40) for _ in range(n)]\n    h = rng.randint(n, n + 60)\n    return [piles, h]\n'),
        gen_large=_code('def gen_large(rng):\n    piles = [rng.randint(1, 10**9) for _ in range(80000)]\n    return [piles, len(piles) + 50000]\n'),
    ),
    'daily-temperatures': dict(
        brute=_code('class Solution:\n    def dailyTemperatures(self, temperatures):\n        ans = [0] * len(temperatures)\n        for i in range(len(temperatures)):\n            for j in range(i + 1, len(temperatures)):\n                if temperatures[j] > temperatures[i]:\n                    ans[i] = j - i\n                    break\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(30, 100) for _ in range(rng.randint(1, 35))]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[rng.randint(30, 100) for _ in range(250000)]]\n'),
    ),
    'next-greater-element-ii': dict(
        brute=_code('class Solution:\n    def nextGreaterElements(self, nums):\n        n = len(nums)\n        ans = [-1] * n\n        for i in range(n):\n            for step in range(1, n):\n                x = nums[(i + step) % n]\n                if x > nums[i]:\n                    ans[i] = x\n                    break\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(-10, 10) for _ in range(rng.randint(1, 30))]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[rng.randint(-10000, 10000) for _ in range(250000)]]\n'),
    ),
    'largest-rectangle-in-histogram': dict(
        brute=_code('class Solution:\n    def largestRectangleArea(self, heights):\n        best = 0\n        n = len(heights)\n        for i in range(n):\n            mn = 10**18\n            for j in range(i, n):\n                mn = min(mn, heights[j])\n                best = max(best, mn * (j - i + 1))\n        return best\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(0, 15) for _ in range(rng.randint(1, 30))]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[rng.randint(0, 10000) for _ in range(250000)]]\n'),
    ),
    'kth-largest-element-in-an-array': dict(
        brute=_code('class Solution:\n    def findKthLargest(self, nums, k):\n        arr = nums[:]\n        for _ in range(k - 1):\n            m = max(arr)\n            arr.remove(m)\n        return max(arr)\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(1, 30)\n    return [[rng.randint(-30, 30) for _ in range(n)], rng.randint(1, n)]\n'),
        gen_large=_code('def gen_large(rng):\n    nums = [rng.randint(-10**9, 10**9) for _ in range(250000)]\n    return [nums, 300]\n'),
    ),
    'top-k-frequent-elements': dict(
        brute=_code('class Solution:\n    def topKFrequent(self, nums, k):\n        counts = {}\n        for x in nums:\n            counts[x] = counts.get(x, 0) + 1\n        ans = []\n        used = set()\n        for _ in range(k):\n            best = None\n            for x, c in counts.items():\n                if x not in used and (best is None or c > counts[best]):\n                    best = x\n            used.add(best)\n            ans.append(best)\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    distinct = rng.randint(1, 10)\n    vals = list(range(distinct))\n    counts = list(range(1, distinct + 1))\n    rng.shuffle(counts)\n    nums = []\n    for v, cnt in zip(vals, counts):\n        nums.extend([v] * cnt)\n    rng.shuffle(nums)\n    k = rng.randint(1, distinct)\n    return [nums, k]\n'),
        gen_large=_code('def gen_large(rng):\n    nums = []\n    for v in range(160000):\n        nums.extend([v] * (v % 5 + 1))\n    rng.shuffle(nums)\n    return [nums, 100]\n'),
    ),
    'merge-k-sorted-lists': dict(
        brute=_code('class Solution:\n    def mergeKLists(self, lists):\n        vals = []\n        for node in lists:\n            while node:\n                vals.append(node.val)\n                node = node.next\n        vals.sort()\n        dummy = cur = ListNode()\n        for v in vals:\n            cur.next = ListNode(v)\n            cur = cur.next\n        return dummy.next\n'),
        gen_small=_code('def gen_small(rng):\n    lists = []\n    for _ in range(rng.randint(0, 8)):\n        lists.append(sorted(rng.randint(-20, 20) for _ in range(rng.randint(0, 8))))\n    return [lists]\n'),
        gen_large=_code('def gen_large(rng):\n    lists = []\n    for i in range(120):\n        start = rng.randint(-100000, 100000)\n        lists.append(sorted(start + rng.randint(0, 1000000) for _ in range(400)))\n    return [lists]\n'),
    ),
    'reverse-linked-list': dict(
        brute=_code('class Solution:\n    def reverseList(self, head):\n        vals = []\n        while head:\n            vals.append(head.val); head = head.next\n        dummy = cur = ListNode()\n        for v in vals[::-1]:\n            cur.next = ListNode(v); cur = cur.next\n        return dummy.next\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(-20, 20) for _ in range(rng.randint(0, 30))]]\n'),
    ),
    'merge-two-sorted-lists': dict(
        brute=_code('class Solution:\n    def mergeTwoLists(self, list1, list2):\n        vals = []\n        for node in (list1, list2):\n            while node:\n                vals.append(node.val); node = node.next\n        vals.sort()\n        dummy = cur = ListNode()\n        for v in vals:\n            cur.next = ListNode(v); cur = cur.next\n        return dummy.next\n'),
        gen_small=_code('def gen_small(rng):\n    a = sorted(rng.randint(-20, 20) for _ in range(rng.randint(0, 20)))\n    b = sorted(rng.randint(-20, 20) for _ in range(rng.randint(0, 20)))\n    return [a, b]\n'),
    ),
    'remove-nth-node-from-end-of-list': dict(
        brute=_code('class Solution:\n    def removeNthFromEnd(self, head, n):\n        vals = []\n        while head:\n            vals.append(head.val); head = head.next\n        del vals[len(vals) - n]\n        dummy = cur = ListNode()\n        for v in vals:\n            cur.next = ListNode(v); cur = cur.next\n        return dummy.next\n'),
        gen_small=_code('def gen_small(rng):\n    length = rng.randint(1, 25)\n    return [[rng.randint(-20, 20) for _ in range(length)], rng.randint(1, length)]\n'),
    ),
    'maximum-depth-of-binary-tree': dict(
        brute=_code('class Solution:\n    def maxDepth(self, root):\n        if not root:\n            return 0\n        return 1 + max(self.maxDepth(root.left), self.maxDepth(root.right))\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(0, 31)\n    if n == 0:\n        return [[]]\n    arr = []\n    for i in range(n):\n        if i == 0 or rng.random() < 0.75:\n            arr.append(rng.randint(-20, 20))\n        else:\n            arr.append(None)\n    while arr and arr[-1] is None:\n        arr.pop()\n    return [arr]\n'),
    ),
    'binary-tree-level-order-traversal': dict(
        brute=_code('class Solution:\n    def levelOrder(self, root):\n        if not root:\n            return []\n        ans = []\n        q = deque([root])\n        while q:\n            level = []\n            for _ in range(len(q)):\n                node = q.popleft()\n                level.append(node.val)\n                if node.left: q.append(node.left)\n                if node.right: q.append(node.right)\n            ans.append(level)\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(0, 31)\n    if n == 0:\n        return [[]]\n    arr = []\n    for i in range(n):\n        arr.append(rng.randint(-20, 20) if i == 0 or rng.random() < 0.7 else None)\n    while arr and arr[-1] is None:\n        arr.pop()\n    return [arr]\n'),
    ),
    'validate-binary-search-tree': dict(
        brute=_code('class Solution:\n    def isValidBST(self, root):\n        vals = []\n        def dfs(node):\n            if not node: return\n            dfs(node.left); vals.append(node.val); dfs(node.right)\n        dfs(root)\n        return all(vals[i] < vals[i + 1] for i in range(len(vals) - 1))\n'),
        gen_small=_code('def gen_small(rng):\n    if rng.random() < 0.55:\n        vals = sorted(set(rng.randint(-50, 50) for _ in range(rng.randint(0, 18))))\n        arr = []\n        def put(lo, hi, idx):\n            if lo > hi: return\n            mid = (lo + hi) // 2\n            while len(arr) <= idx: arr.append(None)\n            arr[idx] = vals[mid]\n            put(lo, mid - 1, idx * 2 + 1); put(mid + 1, hi, idx * 2 + 2)\n        put(0, len(vals) - 1, 0)\n        while arr and arr[-1] is None: arr.pop()\n        return [arr]\n    n = rng.randint(0, 20)\n    if n == 0: return [[]]\n    arr = [rng.randint(-20, 20) if i == 0 or rng.random() < 0.75 else None for i in range(n)]\n    while arr and arr[-1] is None: arr.pop()\n    return [arr]\n'),
    ),
    'diameter-of-binary-tree': dict(
        brute=_code('class Solution:\n    def diameterOfBinaryTree(self, root):\n        nodes = []\n        parent = {}\n        def walk(node, par=None):\n            if not node: return\n            nodes.append(node); parent[node] = par\n            walk(node.left, node); walk(node.right, node)\n        walk(root)\n        best = 0\n        for start in nodes:\n            q = deque([(start, 0)]); seen = {start}\n            while q:\n                node, dist = q.popleft(); best = max(best, dist)\n                for nxt in (node.left, node.right, parent[node]):\n                    if nxt and nxt not in seen:\n                        seen.add(nxt); q.append((nxt, dist + 1))\n        return best\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(0, 28)\n    if n == 0: return [[]]\n    arr = [rng.randint(-20, 20) if i == 0 or rng.random() < 0.75 else None for i in range(n)]\n    while arr and arr[-1] is None: arr.pop()\n    return [arr]\n'),
    ),
    'number-of-islands': dict(
        brute=_code("class Solution:\n    def numIslands(self, grid):\n        if not grid:\n            return 0\n        m, n = len(grid), len(grid[0])\n        seen = [[False] * n for _ in range(m)]\n        ans = 0\n        for i in range(m):\n            for j in range(n):\n                if grid[i][j] == '1' and not seen[i][j]:\n                    ans += 1\n                    stack = [(i, j)]; seen[i][j] = True\n                    while stack:\n                        x, y = stack.pop()\n                        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):\n                            a, b = x + dx, y + dy\n                            if 0 <= a < m and 0 <= b < n and grid[a][b] == '1' and not seen[a][b]:\n                                seen[a][b] = True; stack.append((a, b))\n        return ans\n"),
        gen_small=_code("def gen_small(rng):\n    rows, cols = rng.randint(1, 8), rng.randint(1, 8)\n    return [[[('1' if rng.random() < 0.4 else '0') for _ in range(cols)] for _ in range(rows)]]\n"),
    ),
    'rotting-oranges': dict(
        brute=_code('class Solution:\n    def orangesRotting(self, grid):\n        m, n = len(grid), len(grid[0])\n        fresh = sum(grid[i][j] == 1 for i in range(m) for j in range(n))\n        rotten = [(i, j) for i in range(m) for j in range(n) if grid[i][j] == 2]\n        minute = 0\n        while fresh:\n            new = []\n            for x, y in rotten:\n                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):\n                    a, b = x + dx, y + dy\n                    if 0 <= a < m and 0 <= b < n and grid[a][b] == 1:\n                        grid[a][b] = 2; fresh -= 1; new.append((a, b))\n            if not new:\n                return -1\n            rotten = new; minute += 1\n        return minute\n'),
        gen_small=_code('def gen_small(rng):\n    rows, cols = rng.randint(1, 7), rng.randint(1, 7)\n    return [[[rng.choice([0, 1, 1, 2]) for _ in range(cols)] for _ in range(rows)]]\n'),
    ),
    'course-schedule': dict(
        brute=_code('class Solution:\n    def canFinish(self, numCourses, prerequisites):\n        graph = [[] for _ in range(numCourses)]\n        for a, b in prerequisites:\n            graph[b].append(a)\n        visiting = [0] * numCourses\n        def dfs(x):\n            if visiting[x] == 1: return False\n            if visiting[x] == 2: return True\n            visiting[x] = 1\n            for y in graph[x]:\n                if not dfs(y): return False\n            visiting[x] = 2\n            return True\n        return all(dfs(i) for i in range(numCourses))\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(1, 10)\n    edges = set()\n    for _ in range(rng.randint(0, n * 2)):\n        a, b = rng.randrange(n), rng.randrange(n)\n        if a != b:\n            edges.add((a, b))\n    return [n, [list(e) for e in edges]]\n'),
        gen_large=_code('def gen_large(rng):\n    n = 80000\n    return [n, [[i + 1, i] for i in range(n - 1)]]\n'),
    ),
    'number-of-provinces': dict(
        brute=_code('class Solution:\n    def findCircleNum(self, isConnected):\n        n = len(isConnected)\n        seen = [False] * n\n        ans = 0\n        for i in range(n):\n            if not seen[i]:\n                ans += 1\n                stack = [i]; seen[i] = True\n                while stack:\n                    x = stack.pop()\n                    for y in range(n):\n                        if isConnected[x][y] and not seen[y]:\n                            seen[y] = True; stack.append(y)\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(1, 9)\n    mat = [[0] * n for _ in range(n)]\n    for i in range(n):\n        mat[i][i] = 1\n    for i in range(n):\n        for j in range(i + 1, n):\n            if rng.random() < 0.3:\n                mat[i][j] = mat[j][i] = 1\n    return [mat]\n'),
    ),
    'subsets': dict(
        brute=_code('class Solution:\n    def subsets(self, nums):\n        ans = []\n        n = len(nums)\n        for mask in range(1 << n):\n            cur = []\n            for i in range(n):\n                if mask >> i & 1:\n                    cur.append(nums[i])\n            ans.append(cur)\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(0, 8)\n    nums = rng.sample(range(-20, 21), n)\n    return [nums]\n'),
    ),
    'permutations': dict(
        brute=_code('class Solution:\n    def permute(self, nums):\n        if not nums:\n            return [[]]\n        ans = []\n        for i, x in enumerate(nums):\n            for rest in self.permute(nums[:i] + nums[i + 1:]):\n                ans.append([x] + rest)\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(1, 7)\n    return [rng.sample(range(-10, 20), n)]\n'),
    ),
    'combination-sum': dict(
        brute=_code('class Solution:\n    def combinationSum(self, candidates, target):\n        candidates = sorted(candidates)\n        found = set()\n        def rec(start, remain, path):\n            if remain == 0:\n                found.add(tuple(path)); return\n            if remain < 0:\n                return\n            for i in range(start, len(candidates)):\n                rec(i, remain - candidates[i], path + [candidates[i]])\n        rec(0, target, [])\n        return [list(x) for x in found]\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(1, 6)\n    candidates = sorted(rng.sample(range(2, 16), n))\n    return [candidates, rng.randint(1, 35)]\n'),
    ),
    'generate-parentheses': dict(
        brute=_code("class Solution:\n    def generateParenthesis(self, n):\n        ans = []\n        def valid(s):\n            bal = 0\n            for ch in s:\n                bal += 1 if ch == '(' else -1\n                if bal < 0: return False\n            return bal == 0\n        def rec(s):\n            if len(s) == 2 * n:\n                if valid(s): ans.append(s)\n                return\n            rec(s + '('); rec(s + ')')\n        rec('')\n        return ans\n"),
        gen_small=_code('def gen_small(rng):\n    return [rng.randint(1, 7)]\n'),
    ),
    'climbing-stairs': dict(
        brute=_code('class Solution:\n    def climbStairs(self, n):\n        def rec(k):\n            if k <= 1: return 1\n            return rec(k - 1) + rec(k - 2)\n        return rec(n)\n'),
        gen_small=_code('def gen_small(rng):\n    return [rng.randint(1, 20)]\n'),
    ),
    'house-robber': dict(
        brute=_code('class Solution:\n    def rob(self, nums):\n        best = 0\n        n = len(nums)\n        for mask in range(1 << n):\n            ok = True; total = 0\n            for i in range(n):\n                if mask >> i & 1:\n                    if i and (mask >> (i - 1) & 1):\n                        ok = False; break\n                    total += nums[i]\n            if ok: best = max(best, total)\n        return best\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(0, 30) for _ in range(rng.randint(1, 16))]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[rng.randint(0, 1000) for _ in range(250000)]]\n'),
    ),
    'coin-change': dict(
        brute=_code('class Solution:\n    def coinChange(self, coins, amount):\n        best = [10**9]\n        coins = sorted(coins, reverse=True)\n        def rec(i, remain, used):\n            if remain == 0:\n                best[0] = min(best[0], used); return\n            if i == len(coins) or used >= best[0]:\n                return\n            coin = coins[i]\n            for cnt in range(remain // coin, -1, -1):\n                rec(i + 1, remain - cnt * coin, used + cnt)\n        rec(0, amount, 0)\n        return -1 if best[0] == 10**9 else best[0]\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(1, 5)\n    coins = sorted(rng.sample(range(1, 15), n))\n    return [coins, rng.randint(0, 40)]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[1, 3, 4, 7, 11, 19, 31, 43], 250000]\n'),
    ),
    'longest-increasing-subsequence': dict(
        brute=_code('class Solution:\n    def lengthOfLIS(self, nums):\n        best = 0\n        n = len(nums)\n        for mask in range(1 << n):\n            seq = []\n            ok = True\n            for i in range(n):\n                if mask >> i & 1:\n                    if seq and nums[i] <= seq[-1]:\n                        ok = False; break\n                    seq.append(nums[i])\n            if ok: best = max(best, len(seq))\n        return best\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(-20, 20) for _ in range(rng.randint(0, 15))]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[rng.randint(-1000000, 1000000) for _ in range(250000)]]\n'),
    ),
    'longest-common-subsequence': dict(
        brute=_code('class Solution:\n    def longestCommonSubsequence(self, text1, text2):\n        best = 0\n        def rec(i, j, cur):\n            nonlocal best\n            if i == len(text1) or j == len(text2):\n                best = max(best, cur); return\n            if text1[i] == text2[j]:\n                rec(i + 1, j + 1, cur + 1)\n            rec(i + 1, j, cur)\n            rec(i, j + 1, cur)\n        rec(0, 0, 0)\n        return best\n'),
        gen_small=_code('def gen_small(rng):\n    alphabet = "abc"\n    return ["".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8))), "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8)))]\n'),
        gen_large=_code("def gen_large(rng):\n    return [''.join(rng.choice('abcd') for _ in range(1000)), ''.join(rng.choice('abcd') for _ in range(1000))]\n"),
    ),
    'edit-distance': dict(
        brute=_code('class Solution:\n    def minDistance(self, word1, word2):\n        from functools import lru_cache\n        @lru_cache(None)\n        def rec(i, j):\n            if i == len(word1): return len(word2) - j\n            if j == len(word2): return len(word1) - i\n            if word1[i] == word2[j]: return rec(i + 1, j + 1)\n            return 1 + min(rec(i + 1, j), rec(i, j + 1), rec(i + 1, j + 1))\n        return rec(0, 0)\n'),
        gen_small=_code('def gen_small(rng):\n    alphabet = "abcd"\n    return ["".join(rng.choice(alphabet) for _ in range(rng.randint(0, 9))), "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 9)))]\n'),
        gen_large=_code("def gen_large(rng):\n    return [''.join(rng.choice('abcd') for _ in range(1000)), ''.join(rng.choice('abcd') for _ in range(1000))]\n"),
    ),
    'merge-intervals': dict(
        brute=_code('class Solution:\n    def merge(self, intervals):\n        changed = True\n        arr = [x[:] for x in intervals]\n        while changed:\n            changed = False\n            out = []\n            used = [False] * len(arr)\n            for i in range(len(arr)):\n                if used[i]: continue\n                a, b = arr[i]\n                used[i] = True\n                for j in range(i + 1, len(arr)):\n                    if not used[j] and not (arr[j][1] < a or arr[j][0] > b):\n                        a = min(a, arr[j][0]); b = max(b, arr[j][1])\n                        used[j] = True; changed = True\n                out.append([a, b])\n            arr = out\n        return arr\n'),
        gen_small=_code('def gen_small(rng):\n    intervals = []\n    for _ in range(rng.randint(1, 18)):\n        a = rng.randint(0, 30); b = rng.randint(a, a + rng.randint(0, 8))\n        intervals.append([a, b])\n    return [intervals]\n'),
        gen_large=_code('def gen_large(rng):\n    intervals = []\n    for _ in range(160000):\n        a = rng.randint(0, 1000000)\n        intervals.append([a, a + rng.randint(0, 1000)])\n    return [intervals]\n'),
    ),
    'jump-game': dict(
        brute=_code('class Solution:\n    def canJump(self, nums):\n        reachable = {0}\n        for i in range(len(nums)):\n            if i in reachable:\n                for j in range(i + 1, min(len(nums), i + nums[i] + 1)):\n                    reachable.add(j)\n        return bool(nums) and len(nums) - 1 in reachable\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(1, 25)\n    return [[rng.randint(0, 6) for _ in range(n)]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[rng.randint(1, 8) for _ in range(250000)]]\n'),
    ),
    'non-overlapping-intervals': dict(
        brute=_code('class Solution:\n    def eraseOverlapIntervals(self, intervals):\n        intervals = sorted(intervals)\n        n = len(intervals)\n        best = 0\n        for mask in range(1 << n):\n            chosen = [intervals[i] for i in range(n) if mask >> i & 1]\n            ok = True\n            for i in range(len(chosen)):\n                for j in range(i + 1, len(chosen)):\n                    a, b = chosen[i], chosen[j]\n                    if not (a[1] <= b[0] or b[1] <= a[0]):\n                        ok = False; break\n                if not ok: break\n            if ok: best = max(best, len(chosen))\n        return n - best\n'),
        gen_small=_code('def gen_small(rng):\n    intervals = []\n    for _ in range(rng.randint(1, 12)):\n        a = rng.randint(-15, 15); b = a + rng.randint(1, 8)\n        intervals.append([a, b])\n    return [intervals]\n'),
        gen_large=_code('def gen_large(rng):\n    intervals = []\n    for _ in range(160000):\n        a = rng.randint(-1000000, 1000000)\n        intervals.append([a, a + rng.randint(1, 1000)])\n    return [intervals]\n'),
    ),
    'network-delay-time': dict(
        brute=_code('class Solution:\n    def networkDelayTime(self, times, n, k):\n        INF = 10**18\n        dist = [INF] * (n + 1)\n        dist[k] = 0\n        for _ in range(n - 1):\n            changed = False\n            for u, v, w in times:\n                if dist[u] + w < dist[v]:\n                    dist[v] = dist[u] + w; changed = True\n            if not changed: break\n        ans = max(dist[1:])\n        return -1 if ans >= INF else ans\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(1, 9)\n    edges = set()\n    times = []\n    for _ in range(rng.randint(0, n * (n - 1))):\n        u, v = rng.randrange(1, n + 1), rng.randrange(1, n + 1)\n        if u != v and (u, v) not in edges:\n            edges.add((u, v)); times.append([u, v, rng.randint(1, 12)])\n    return [times, n, rng.randint(1, n)]\n'),
        gen_large=_code('def gen_large(rng):\n    n = 80000\n    times = [[i, i + 1, 1] for i in range(1, n)]\n    for _ in range(80000):\n        u = rng.randint(1, n - 1); v = rng.randint(u + 1, n)\n        times.append([u, v, rng.randint(1, 20)])\n    return [times, n, 1]\n'),
    ),
    'redundant-connection': dict(
        brute=_code('class Solution:\n    def findRedundantConnection(self, edges):\n        parent = {}\n        def find(x):\n            parent.setdefault(x, x)\n            while parent[x] != x:\n                x = parent[x]\n            return x\n        def connected(a, b):\n            return find(a) == find(b)\n        for a, b in edges:\n            if connected(a, b):\n                return [a, b]\n            parent[find(a)] = find(b)\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(3, 12)\n    edges = []\n    used = set()\n    for i in range(2, n + 1):\n        p = rng.randint(1, i - 1)\n        edges.append([p, i])\n        used.add(tuple(sorted((p, i))))\n    while True:\n        a, b = rng.sample(range(1, n + 1), 2)\n        if tuple(sorted((a, b))) not in used:\n            edges.append([a, b])\n            return [edges]\n'),
        gen_large=_code('def gen_large(rng):\n    n = 250000\n    edges = [[i, i + 1] for i in range(1, n)]\n    edges.append([1, n])\n    return [edges]\n'),
    ),
    'accounts-merge': dict(
        brute=_code('class Solution:\n    def accountsMerge(self, accounts):\n        n = len(accounts)\n        parent = list(range(n))\n        def find(x):\n            while parent[x] != x:\n                x = parent[x]\n            return x\n        def union(a, b):\n            ra, rb = find(a), find(b)\n            if ra != rb: parent[rb] = ra\n        owner = {}\n        for i, acc in enumerate(accounts):\n            for email in acc[1:]:\n                if email in owner: union(i, owner[email])\n                else: owner[email] = i\n        groups = {}\n        for i, acc in enumerate(accounts):\n            root = find(i)\n            groups.setdefault(root, set()).update(acc[1:])\n        return [[accounts[i][0]] + sorted(emails) for i, emails in groups.items()]\n'),
        gen_small=_code("def gen_small(rng):\n    names = ['Ann', 'Bob', 'Cid', 'Di']\n    accounts = []\n    for name in names:\n        pool = [f'{name.lower()}{i}@x.com' for i in range(8)]\n        for _ in range(rng.randint(0, 3)):\n            emails = rng.sample(pool, rng.randint(1, 4))\n            accounts.append([name] + emails)\n    if not accounts:\n        accounts.append(['Ann', 'ann0@x.com'])\n    rng.shuffle(accounts)\n    return [accounts]\n"),
        gen_large=_code("def gen_large(rng):\n    accounts = []\n    for i in range(90000):\n        accounts.append(['N' + str(i % 10), f'e{i}a@x.com', f'e{i}b@x.com'])\n    return [accounts]\n"),
    ),
    'partition-equal-subset-sum': dict(
        brute=_code('class Solution:\n    def canPartition(self, nums):\n        total = sum(nums)\n        if total % 2: return False\n        target = total // 2\n        n = len(nums)\n        for mask in range(1 << n):\n            s = 0\n            for i in range(n):\n                if mask >> i & 1:\n                    s += nums[i]\n            if s == target:\n                return True\n        return False\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(1, 20) for _ in range(rng.randint(1, 15))]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[100 for _ in range(200)]]\n'),
    ),
    'coin-change-ii': dict(
        brute=_code('class Solution:\n    def change(self, amount, coins):\n        coins = sorted(coins)\n        ans = 0\n        def rec(start, remain):\n            nonlocal ans\n            if remain == 0:\n                ans += 1; return\n            for i in range(start, len(coins)):\n                if coins[i] <= remain:\n                    rec(i, remain - coins[i])\n        rec(0, amount)\n        return ans\n'),
        gen_small=_code('def gen_small(rng):\n    n = rng.randint(1, 5)\n    coins = sorted(rng.sample(range(1, 12), n))\n    return [rng.randint(0, 28), coins]\n'),
        gen_large=_code('def gen_large(rng):\n    return [5000, list(range(1, 301))]\n'),
    ),
    'minimum-path-sum': dict(
        brute=_code('class Solution:\n    def minPathSum(self, grid):\n        m, n = len(grid), len(grid[0])\n        best = [10**18]\n        def rec(i, j, total):\n            total += grid[i][j]\n            if i == m - 1 and j == n - 1:\n                best[0] = min(best[0], total); return\n            if i + 1 < m: rec(i + 1, j, total)\n            if j + 1 < n: rec(i, j + 1, total)\n        rec(0, 0, 0)\n        return best[0]\n'),
        gen_small=_code('def gen_small(rng):\n    rows, cols = rng.randint(1, 5), rng.randint(1, 5)\n    return [[[rng.randint(0, 15) for _ in range(cols)] for _ in range(rows)]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[[rng.randint(0, 100) for _ in range(500)] for _ in range(500)]]\n'),
    ),
    'longest-palindromic-subsequence': dict(
        brute=_code('class Solution:\n    def longestPalindromeSubseq(self, s):\n        best = 0\n        n = len(s)\n        for mask in range(1 << n):\n            t = []\n            for i in range(n):\n                if mask >> i & 1:\n                    t.append(s[i])\n            if t == t[::-1]:\n                best = max(best, len(t))\n        return best\n'),
        gen_small=_code("def gen_small(rng):\n    return [''.join(rng.choice('abcd') for _ in range(rng.randint(1, 14)))]\n"),
        gen_large=_code("def gen_large(rng):\n    return [''.join(rng.choice('abcd') for _ in range(1000))]\n"),
    ),
    'burst-balloons': dict(
        brute=_code('class Solution:\n    def maxCoins(self, nums):\n        from functools import lru_cache\n        arr = [1] + nums + [1]\n        @lru_cache(None)\n        def rec(left, right):\n            if left + 1 >= right:\n                return 0\n            best = 0\n            for mid in range(left + 1, right):\n                best = max(best, arr[left] * arr[mid] * arr[right] + rec(left, mid) + rec(mid, right))\n            return best\n        return rec(0, len(arr) - 1)\n'),
        gen_small=_code('def gen_small(rng):\n    return [[rng.randint(1, 8) for _ in range(rng.randint(1, 9))]]\n'),
        gen_large=_code('def gen_large(rng):\n    return [[rng.randint(1, 100) for _ in range(180)]]\n'),
    ),
}
