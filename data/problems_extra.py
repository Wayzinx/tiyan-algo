from problems import P


PROBLEMS_EXTRA = [
    P(
        "network-delay-time", "网络延迟时间", "graph", "medium", 743,
        "有 `n` 个节点，若干有向边 `times[i] = [u, v, w]` 表示信号从 `u` 到 `v` 需要 `w` 时间。\n\n从节点 `k` 发出信号，返回所有节点都收到信号的最短总等待时间；若存在节点不可达，返回 -1。",
        [
            {"input": "times = [[2,1,1],[2,3,1],[3,4,1]], n = 4, k = 2", "output": "2", "note": "最慢的 4 号节点在 2 个时间单位后收到"},
            {"input": "times = [[1,2,1]], n = 2, k = 2", "output": "-1", "note": "从 2 出发到不了 1"},
        ],
        ["1 <= n <= 100", "0 <= len(times) <= 6000", "times 中的边权为正整数", "节点编号从 1 到 n"],
        "networkDelayTime", [("times", "List[List[int]]"), ("n", "int"), ("k", "int")], "int",
        [
            [[[2,1,1],[2,3,1],[3,4,1]], 4, 2],
            [[[1,2,1]], 2, 2],
            [[], 1, 1],
            [[[1,2,5],[1,3,2],[3,2,1]], 3, 1],
            [[[1,2,1],[2,3,2],[1,3,5]], 3, 1],
            [[[1,2,1],[2,1,3]], 2, 1],
            [[[1,2,4],[1,3,1],[3,4,1],[4,2,1],[2,5,1]], 5, 1],
        ],
        """
        class Solution:
            def networkDelayTime(self, times, n, k):
                graph = defaultdict(list)
                for u, v, w in times:
                    graph[u].append((v, w))
                dist = [float('inf')] * (n + 1)
                dist[k] = 0
                heap = [(0, k)]
                while heap:
                    d, node = heapq.heappop(heap)
                    if d != dist[node]:
                        continue
                    for nxt, weight in graph[node]:
                        nd = d + weight
                        if nd < dist[nxt]:
                            dist[nxt] = nd
                            heapq.heappush(heap, (nd, nxt))
                ans = max(dist[1:])
                return -1 if ans == float('inf') else ans
        """,
        "时间 O((n + m) log n)，空间 O(n + m)",
        ["题型：最短路。边权为正，适合用 Dijkstra。", "用邻接表保存出边，堆里放当前可到达的最短候选距离。", "所有最短距离求出后，答案是最大距离；仍为无穷说明有节点不可达。"],
        "从起点到所有点的最短路里，最晚收到信号的时间就是最大最短距离。",
        ["把边当成无向边会误判可达性", "没有丢弃堆里的过期距离会做很多无效扩展"],
    ),
    P(
        "redundant-connection", "冗余连接", "graph", "medium", 684,
        "给定一棵树额外加上一条边后的无向图，边按输入顺序给出。\n\n返回那条会让图出现环的边；如果多条边看起来可删，按扫描顺序返回最后触发环的那条。",
        [
            {"input": "edges = [[1,2],[1,3],[2,3]]", "output": "[2,3]", "note": "加入 [2,3] 前 2 和 3 已经连通"},
            {"input": "edges = [[1,2],[2,3],[3,4],[1,4],[1,5]]", "output": "[1,4]", "note": "[1,4] 闭合了 1-2-3-4 的环"},
        ],
        ["3 <= len(edges) <= 1000", "edges[i].length == 2", "图由一棵树加一条边得到", "节点编号为正整数"],
        "findRedundantConnection", [("edges", "List[List[int]]")], "List[int]",
        [
            [[[1,2],[1,3],[2,3]]],
            [[[1,2],[2,3],[3,4],[1,4],[1,5]]],
            [[[1,2],[2,3],[1,3]]],
            [[[1,4],[3,4],[1,3],[1,2],[4,5]]],
            [[[1,2],[2,3],[3,1]]],
            [[[2,3],[3,4],[1,5],[4,5],[1,2]]],
        ],
        """
        class Solution:
            def findRedundantConnection(self, edges):
                parent = {}
                def find(x):
                    parent.setdefault(x, x)
                    if parent[x] != x:
                        parent[x] = find(parent[x])
                    return parent[x]
                for a, b in edges:
                    ra, rb = find(a), find(b)
                    if ra == rb:
                        return [a, b]
                    parent[rb] = ra
        """,
        "时间 O(n α(n))，空间 O(n)",
        ["题型：并查集。无向图逐边加入时，若两个端点已连通，再加这条边就成环。", "为每个节点维护集合代表；扫描边前先找两个端点的根。", "根相同直接返回当前边，否则合并两个集合。"],
        "树中任意两点已有唯一路径，再连同一连通块内的两点就会产生环。",
        ["先合并再判断会错过成环边", "只用入度思路不适合无向图"],
    ),
    P(
        "accounts-merge", "账户合并", "graph", "medium", 721,
        "每个账户包含一个用户名和若干邮箱。只要两个账户共享至少一个邮箱，就认为属于同一个人。\n\n合并属于同一人的账户，结果中用户名放在第一位，后续邮箱按字典序排列；多个账户组的顺序不重要。",
        [
            {"input": "accounts = [['John','a@mail','b@mail'],['John','b@mail','c@mail'],['Mary','m@mail']]", "output": "[['John','a@mail','b@mail','c@mail'],['Mary','m@mail']]", "note": "前两个 John 共享 b@mail"},
            {"input": "accounts = [['A','x@mail'],['A','y@mail']]", "output": "[['A','x@mail'],['A','y@mail']]", "note": "没有共享邮箱，不合并"},
        ],
        ["1 <= len(accounts) <= 1000", "每个账户至少包含 1 个邮箱", "邮箱字符串可作为唯一标识", "同组输出邮箱需要升序"],
        "accountsMerge", [("accounts", "List[List[str]]")], "List[List[str]]",
        [
            [[['John','a@mail','b@mail'],['John','b@mail','c@mail'],['Mary','m@mail']]],
            [[['A','x@mail'],['A','y@mail']]],
            [[['Gabe','g1','g2'],['Gabe','g3'],['Gabe','g2','g4']]],
            [[['Alex','a1'],['Bob','b1','b2'],['Bob','b2','b3']]],
            [[['Z','z3','z1','z2']]],
            [[['K','k1','k2'],['K','k3','k4'],['K','k2','k4']]],
        ],
        """
        class Solution:
            def accountsMerge(self, accounts):
                parent = list(range(len(accounts)))
                def find(x):
                    if parent[x] != x:
                        parent[x] = find(parent[x])
                    return parent[x]
                def union(a, b):
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        parent[rb] = ra
                owner = {}
                for i, account in enumerate(accounts):
                    for email in account[1:]:
                        if email in owner:
                            union(i, owner[email])
                        else:
                            owner[email] = i
                groups = defaultdict(set)
                for i, account in enumerate(accounts):
                    groups[find(i)].update(account[1:])
                return [[accounts[root][0]] + sorted(emails) for root, emails in groups.items()]
        """,
        "时间 O(E α(A) + E log E)，空间 O(A + E)",
        ["题型：并查集。邮箱是账户之间的连接边。", "记录每个邮箱第一次出现的账户；再次遇到同邮箱就合并两个账户。", "最后按集合代表收集邮箱，排序后拼上用户名。"],
        "共享邮箱让账户连成同一连通块，合并每个连通块的邮箱集合即可。",
        ["只按用户名合并会把同名不同人混在一起", "输出邮箱不排序会导致结果不稳定"],
        compare="unordered",
    ),
    P(
        "partition-equal-subset-sum", "分割等和子集", "dp", "medium", 416,
        "给定只含正整数的数组，判断能否把它分成两个子集，使两个子集的元素和相同。\n\n等价于能否选出若干数字，凑出总和的一半。",
        [
            {"input": "nums = [1,5,11,5]", "output": "True", "note": "可分成 [11] 和 [1,5,5]"},
            {"input": "nums = [1,2,3,5]", "output": "False", "note": "总和为 11，无法平分"},
        ],
        ["1 <= len(nums) <= 200", "1 <= nums[i] <= 100", "只需要返回是否存在一种分法"],
        "canPartition", [("nums", "List[int]")], "bool",
        [
            [[1,5,11,5]], [[1,2,3,5]], [[2,2,1,1]], [[100]], [[1,1]], [[3,3,3,4,5]], [[2,2,3,5]],
        ],
        """
        class Solution:
            def canPartition(self, nums):
                total = sum(nums)
                if total % 2:
                    return False
                target = total // 2
                dp = [False] * (target + 1)
                dp[0] = True
                for x in nums:
                    for s in range(target, x - 1, -1):
                        dp[s] = dp[s] or dp[s - x]
                return dp[target]
        """,
        "时间 O(n * sum)，空间 O(sum)",
        ["题型：0-1 背包。每个数只能选或不选一次。", "总和为奇数时一定不能平分。", "目标是凑出 total/2，倒序更新避免同一个数被重复使用。"],
        "平分数组就是从元素中选一部分凑出总和的一半。",
        ["正序更新会把 0-1 背包写成完全背包", "忘记奇偶判断会浪费计算并可能写错边界"],
    ),
    P(
        "coin-change-ii", "零钱兑换 II", "dp", "medium", 518,
        "给定金额 `amount` 和若干硬币面额，每种硬币可以使用任意多次。\n\n返回凑出该金额的组合数；组合只看每种硬币用了几个，不区分排列顺序。",
        [
            {"input": "amount = 5, coins = [1,2,5]", "output": "4", "note": "5、2+2+1、2+1+1+1、全 1"},
            {"input": "amount = 3, coins = [2]", "output": "0", "note": "无法凑出奇数金额"},
        ],
        ["0 <= amount <= 5000", "1 <= len(coins) <= 300", "1 <= coins[i] <= 5000", "答案在 32 位整数范围内"],
        "change", [("amount", "int"), ("coins", "List[int]")], "int",
        [
            [5, [1,2,5]], [3, [2]], [10, [10]], [0, [1,2,3]], [4, [1,2,3]], [7, [2,3,6,7]], [12, [1,3,4]],
        ],
        """
        class Solution:
            def change(self, amount, coins):
                dp = [0] * (amount + 1)
                dp[0] = 1
                for coin in coins:
                    for s in range(coin, amount + 1):
                        dp[s] += dp[s - coin]
                return dp[amount]
        """,
        "时间 O(amount * len(coins))，空间 O(amount)",
        ["题型：完全背包计数。每个硬币可以用多次。", "外层遍历硬币、内层正序遍历金额，可以避免排列重复。", "`dp[0]=1` 表示凑出 0 元有一种空组合。"],
        "组合计数要固定硬币顺序，让每种组合只在它的最大硬币被处理时贡献一次。",
        ["把金额放外层会统计排列数", "忘记初始化 dp[0] 会让所有状态保持 0"],
    ),
    P(
        "minimum-path-sum", "最小路径和", "dp", "medium", 64,
        "给定一个非负整数网格，从左上角走到右下角。每一步只能向右或向下。\n\n返回路径经过格子的数字之和的最小值。",
        [
            {"input": "grid = [[1,3,1],[1,5,1],[4,2,1]]", "output": "7", "note": "路径 1-3-1-1-1"},
            {"input": "grid = [[1,2,3],[4,5,6]]", "output": "12", "note": "1-2-3-6"},
        ],
        ["1 <= m,n <= 200", "0 <= grid[i][j] <= 200", "只能向右或向下移动"],
        "minPathSum", [("grid", "List[List[int]]")], "int",
        [
            [[[1,3,1],[1,5,1],[4,2,1]]], [[[1,2,3],[4,5,6]]], [[[5]]], [[[1,2],[1,1]]], [[[0,0,0],[0,1,0]]], [[[9,1,4],[2,8,1],[1,1,1]]],
        ],
        """
        class Solution:
            def minPathSum(self, grid):
                m, n = len(grid), len(grid[0])
                dp = [float('inf')] * n
                dp[0] = 0
                for i in range(m):
                    for j in range(n):
                        if j == 0:
                            dp[j] = dp[j] + grid[i][j]
                        else:
                            dp[j] = min(dp[j], dp[j - 1]) + grid[i][j]
                return dp[-1]
        """,
        "时间 O(mn)，空间 O(n)",
        ["题型：网格 DP。到一个格子只可能来自上方或左方。", "用一维数组保存上一行到当前列的最小代价。", "当前格答案是 `min(上方, 左方) + 当前值`。"],
        "每个格子的最优路径只依赖上方和左方两个已计算状态。",
        ["第一行、第一列边界容易初始化错", "允许向上或向左会改变题意"],
    ),
    P(
        "longest-palindromic-subsequence", "最长回文子序列", "dp", "medium", 516,
        "给定字符串 `s`，可以删除任意字符但不能改变剩余字符的相对顺序。\n\n返回能得到的最长回文子序列长度。",
        [
            {"input": "s = 'bbbab'", "output": "4", "note": "可取 bbbb"},
            {"input": "s = 'cbbd'", "output": "2", "note": "可取 bb"},
        ],
        ["1 <= len(s) <= 1000", "s 由小写英文字母组成", "子序列不要求连续"],
        "longestPalindromeSubseq", [("s", "str")], "int",
        [["bbbab"], ["cbbd"], ["a"], ["aaaa"], ["abcde"], ["agbdba"], ["character"]],
        """
        class Solution:
            def longestPalindromeSubseq(self, s):
                n = len(s)
                dp = [[0] * n for _ in range(n)]
                for i in range(n - 1, -1, -1):
                    dp[i][i] = 1
                    for j in range(i + 1, n):
                        if s[i] == s[j]:
                            dp[i][j] = dp[i + 1][j - 1] + 2
                        else:
                            dp[i][j] = max(dp[i + 1][j], dp[i][j - 1])
                return dp[0][n - 1]
        """,
        "时间 O(n²)，空间 O(n²)",
        ["题型：区间 DP。状态表示子串 s[i:j+1] 内的最长回文子序列。", "两端字符相等时，可以把它们一起放进答案。", "两端不等时，分别丢掉左端或右端取最大。"],
        "回文子序列的决策围绕区间两端字符是否配对。",
        ["把题目当成最长回文子串会要求连续而误判", "遍历顺序必须保证内层区间已经算好"],
    ),
    P(
        "burst-balloons", "戳气球", "dp", "hard", 312,
        "一排气球上写着正整数。每次戳破位置 `i` 的气球，得分为它左右还未戳破气球数值与自身数值的乘积；边界外按 1 处理。\n\n返回把所有气球戳破能得到的最高分。",
        [
            {"input": "nums = [3,1,5,8]", "output": "167", "note": "选择合适顺序可以得到最高分 167"},
            {"input": "nums = [1,5]", "output": "10", "note": "先戳 1 再戳 5"},
        ],
        ["1 <= len(nums) <= 300", "0 <= nums[i] <= 100", "边界虚拟气球的值为 1"],
        "maxCoins", [("nums", "List[int]")], "int",
        [[[3,1,5,8]], [[1,5]], [[1]], [[7,9,8,0,7]], [[2,2,2]], [[1,2,3,4]], [[8,2,6,8,1]]],
        """
        class Solution:
            def maxCoins(self, nums):
                nums = [x for x in nums if x > 0]
                arr = [1] + nums + [1]
                n = len(arr)
                dp = [[0] * n for _ in range(n)]
                for length in range(2, n):
                    for left in range(0, n - length):
                        right = left + length
                        best = 0
                        for mid in range(left + 1, right):
                            best = max(best, dp[left][mid] + dp[mid][right] + arr[left] * arr[mid] * arr[right])
                        dp[left][right] = best
                return dp[0][n - 1]
        """,
        "时间 O(n³)，空间 O(n²)",
        ["题型：区间 DP。正着想第一个戳谁会让左右邻居不断变化。", "反过来枚举某个区间里最后戳破的气球，它的左右邻居就是区间边界。", "按区间长度递增计算，枚举最后一个气球位置更新最大得分。"],
        "把“最后戳哪一个”作为决策，动态边界就变成固定区间边界。",
        ["按第一个戳的气球划分区间会丢失邻居信息", "区间边界的虚拟 1 不能忘记"],
    ),
]
