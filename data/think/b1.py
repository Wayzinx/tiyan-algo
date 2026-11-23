# 思路阶梯 B1 批：数组、查找、链表、树图、回溯与动态规划。
LADDERS = {
    "two-sum": dict(
        read="在数组里挑两个不同位置，使这两个位置上的数加起来等于目标值，返回那两个下标。",
        steps=[
            dict(k="ask", q="找到加起来等于目标值的一对数后，返回什么？",
                 options=["两个数的下标，顺序不限", "两个数的值，按升序返回", "能凑出目标值的下标对有多少组"], answer=0,
                 why="“返回下标”意味着找到数还不够，得知道它在原数组的位置；“恰好一组”则意味着一找到就结束，不需要累计所有配对。"),
            dict(k="input", q="固定其中一个数 x 后，还要找什么？",
                 options=["值等于 target - x、且位置不同的那个数", "和 x 最接近的另一个数", "从 x 开始和最接近目标值的一段连续区间"], answer=0,
                 why="题眼是“两数之和”：等式里只剩一个未知数，另一个值被 target - x 唯一确定。题目没说这两个位置要相邻，只说不能用同一个位置两次。"),
            dict(k="brute", q="先不管效率，怎样保证枚举到那一对？",
                 options=["对每个 i 枚举 j > i，检查两数之和：O(n²)", "只检查每个 i 和 i + 1：O(n)", "只用最左、最右两个位置不断往中间夹：O(n)"], answer=0,
                 why="每对不同下标总有一个较小的，把它当 i 就一定能枚举到；j 从 i + 1 开始既不会自配，也不会反着重试同一对。原数组无序，不能靠和的大小决定丢掉哪个端点。"),
            dict(k="waste", q="内层循环究竟在替我们查什么？",
                 options=["在一批候选位置里逐个找指定值的补数", "加法太多，应该用前缀和预计算", "同一对下标总被正序和倒序各试一次"], answer=0,
                 why="逐个试 j 其实只是因为不知道补数在哪。如果已经扫过一段，就能把那段出现过的值记下来；碰到 x 时，一次查找就能代替对前面所有位置的扫描。"),
            dict(k="tool", q="用什么结构既能快速判存在，又能取回下标？",
                 options=["哈希表：已扫过的值 → 原下标", "集合：只保存已扫过的值", "把原数组直接按值排序，不保存原下标"], answer=0,
                 why="集合解决了“有没有”，但还得再找对应下标。字典用同一次键查找解决这两件事，也不用像排序那样另行携带原下标。"),
            dict(k="state", q="扫描到位置 i 时，查补数前字典里有哪些位置？",
                 options=["只包含 i 之前的下标；查完再记当前位置", "先写入 i，再查字典，保证当前数也能找到", "字典里只保留前一个位置的值"], answer=0,
                 why="先查后存，命中位置自然小于 i。比如 [3, 3] 配 6，第一个 3 只能入表，第二个 3 才能取出前一个位置；反过来可能返回同一个下标两次。"),
        ],
        brute="""class Solution:
    def twoSum(self, nums, target):
        for left in range(len(nums)):
            for right in range(left + 1, len(nums)):
                if nums[left] + nums[right] == target:
                    return [left, right]
""",
        cloze=dict(
            code="""class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for index, value in enumerate(nums):
            other = ⟦1⟧
            if ⟦2⟧:
                return [seen[other], index]
            ⟦3⟧
""",
            blanks=[dict(a="target - value", hint="把当前数移到等式右边，求出补数"),
                    dict(a="other in seen", hint="补数必须已经在之前的位置出现"),
                    dict(a="seen[value] = index", hint="查完后记录当前值及其原下标")],
        ),
        say="固定一个数，另一个数就是目标减去它。我要返回原下标，所以从左往右扫描，用字典记录此前见过的值和它的下标。每轮先查补数，命中就返回两个下标，没命中再记录当前数，这保证不会用同一个位置两次。哈希查找均摊常数，时间 O(n)，空间 O(n)。",
        trap="别先把当前值放进字典再查，特别是目标等于当前值两倍时。比如 [3, 3] 配 6，要拿第一个 3 的下标，不能把当前位置用两次。",
    ),
    "longest-consecutive-sequence": dict(
        read="把乱序数组里的数字当作库存，找出能拼成的最长一串相邻整数，重复数字只算一次。",
        steps=[
            dict(k="ask", q="对 [100, 4, 2, 1, 3]，应返回什么？",
                 options=["整数 4，表示最长一串的长度", "列表 [1, 2, 3, 4]，表示实际拼成的序列", "整数 2，表示原数组中最长连续递增段的长度"], answer=0,
                 why="题目只问长度，不要求重建那串数字。这里 1、2、3、4 虽然散在不同的位置，但值一个不差，就能得到长度 4。"),
            dict(k="input", q="这里的“连续”约束的是下标还是值？",
                 options=["只约束值：下一个必须恰好比上一个大 1", "只约束下标：必须截取一段原数组", "要求保持原来的下标顺序，但值可以跳过"], answer=0,
                 why="“不要求在原数组里相邻”让我们丢掉原顺序，每个数只问是否存在。“连续整数”又把后继固定成 x + 1，不需要从所有更大的数里挑下一个。"),
            dict(k="brute", q="如果从每个不同的值都试着向上凑，要多慢？",
                 options=["用集合查后继，仍可能走 O(n²) 步", "用集合查后继，每个值必定只查一次，总共 O(n)", "每一步都要枚举哪些数字取舍，总共 O(2ⁿ)"], answer=0,
                 why="可先去重，然后从每个值不停查 x + 1 是否在集合里。对 1 到 n 的完整一串，会分别走 n、n - 1、……步，单次查询快不代表总查询次数少。"),
            dict(k="waste", q="从 1、2、3 分别向上数时，重复在哪里？",
                 options=["同一串的后半部分从多个起点反复走过", "所有最优解都被重复存进了答案数组", "去重时需要把每个数字与其他所有数字比较"], answer=0,
                 why="如果 1 能接到 2，且从 2 能接着走到结尾，从 2 开始只得到从 1 开始的一个更短后缀。已经有左邻居的值没必要再当起点。"),
            dict(k="tool", q="为了只从真正的起点出发，该怎么查？",
                 options=["用集合查 x - 1 是否缺席，缺席才连续查 x + 1", "先排序再用双指针计数，作为接近线性的做法", "用堆反复取最小值，每次取数都是常数时间"], answer=0,
                 why="找起点、找后继，本质上都是问某个值存不存在，不需要有序遍历。集合均摊常数查询；排序扫描也能做对，但这里要求接近线性。"),
            dict(k="state", q="从合法起点 start 向上查，停在哪、长度怎么算？",
                 options=["停在第一个不存在的 stop，长度是 stop - start", "停在第一个不存在的 stop，长度是 stop - start + 1", "遇到空缺也继续查到数组最大值，长度是最大值减起点"], answer=0,
                 why="循环中确认存在的是半开区间 [start, stop)，所以减法正好给出已走过的整数个数。每个数只属于一串，只有该串的最小值能启动扫描。"),
        ],
        brute="""class Solution:
    def longestConsecutive(self, nums):
        values = set(nums)
        best = 0
        for start in values:
            stop = start
            while stop in values:
                stop += 1
            best = max(best, stop - start)
        return best
""",
        cloze=dict(
            code="""class Solution:
    def longestConsecutive(self, nums):
        values = set(nums)
        best = 0
        for start in values:
            if ⟦1⟧:
                stop = start
                while ⟦2⟧:
                    stop += 1
                best = max(best, ⟦3⟧)
        return best
""",
            blanks=[dict(a="start - 1 not in values", hint="没有前驱，才是这一串最左边的值"),
                    dict(a="stop in values", hint="下一个值能接上，就继续找"),
                    dict(a="stop - start", hint="停止位置是第一个缺失的值，不计入长度")],
        ),
        say="这里连续的是数值，不是下标。我先建集合去重，只有找不到前驱 x - 1 时，才从 x 开始逐个查后继；查到第一个缺失值就用它减起点更新最大长度。每段只从最小值扫描一次，每个不同的值最多被扩展走过一次，均摊时间 O(n)，空间 O(n)。",
        trap="外层也要遍历去重后的集合。若遍历原数组，起点重复一万次时，同一段还是会被反复扫；只加“前驱不存在”的判断不够。",
    ),
    "3sum": dict(
        read="挑三个不同位置，使对应数字的和为零，返回所有按数字内容去重后的三元组。",
        steps=[
            dict(k="ask", q="两个不同下标组都对应 [-1, 0, 1]，要返回几次？",
                 options=["一次，结果按三个值去重", "两次，只要下标不同就算不同方案", "找到这组就直接返回，不再找其他值的组合"], answer=0,
                 why="不同下标是选数字时的约束，答案去重却看数字的值。这两件事要分开，例如 [-1, -1, 2] 合法，但前提是数组里真的有两个 -1。"),
            dict(k="input", q="枚举一个数之后，余下问题变成了什么？",
                 options=["从剩余位置找两数，使它们的和等于固定值的相反数", "从剩余位置找三个数抵消固定值", "找一个紧挨固定位置的连续区间，使区间和为零"], answer=0,
                 why="三个数里先固定一个，另外两个的目标和就确定了；题目不返回原下标，也不要求原顺序，因此可以先把相同值排到一起再做这个两数子问题。"),
            dict(k="brute", q="如何直接枚举，又能按值去重？",
                 options=["枚举 i < j < k，和为零就把排好序的值元组放入集合：O(n³)", "先把输入转成集合，再枚举三个不同值：O(n³)", "枚举紧挨的三个位置，把和为零的加入结果：O(n)"], answer=0,
                 why="三个递增下标保证没有复用位置；同一批值按统一顺序放入集合，就算来自不同位置也只保留一次。先对输入去重反而会漏掉两个或三个值相同的合法解。"),
            dict(k="waste", q="固定一个值后，哪部分不必再逐对试？",
                 options=["排序后，能一次排除与某个端点搭配的所有剩余不可能配对", "固定值后另外两个值总是相等，只需要枚举其中一个", "既然只要求和为零，就可以跳过所有负数"], answer=0,
                 why="当前和偏小时，右边已经是剩余最大的值，再换更小的右值也救不了当前左值；偏大则是对称的道理。这让一次比较能排除一批配对，而不是只淘汰当前一对。"),
            dict(k="tool", q="在排序后的剩余区间，怎样找全所有配对？",
                 options=["双指针从两端向内，和偏小移左，偏大移右", "一旦和偏离零，同时移动两端", "对两个端点的下标做二分，总是对半砍掉剩余区间"], answer=0,
                 why="左端向右才能增大和，右端向左才能减小和。每次只丢被证明无解的那个端点；同时移动会把仍可与其他值配对的端点也丢掉。"),
            dict(k="state", q="固定值和内层命中后的两端，如何避免重复答案？",
                 options=["外层跳过相同固定值；命中记一次后，左右都跨过刚用的值", "每轮不论是否命中都移动两端，再根据答案数量判断", "只跳过外层相同固定值，内层相同配对照常加入答案"], answer=0,
                 why="固定值相同，第一次已经能使用其右边所有候选，后面固定相同值不会产生新方案。内层命中后，任一端的值不变时，另一端的配对值也唯一，再用这两个值只会重复。"),
        ],
        brute="""class Solution:
    def threeSum(self, nums):
        values = sorted(nums)
        triples = set()
        for first in range(len(values) - 2):
            for second in range(first + 1, len(values) - 1):
                for third in range(second + 1, len(values)):
                    if values[first] + values[second] + values[third] == 0:
                        triples.add((values[first], values[second], values[third]))
        return [list(triple) for triple in triples]
""",
        cloze=dict(
            code="""class Solution:
    def threeSum(self, nums):
        nums.sort()
        result = []
        for first in range(len(nums) - 2):
            if ⟦1⟧:
                continue
            if nums[first] > 0:
                break
            left, right = ⟦2⟧
            while left < right:
                total = nums[first] + nums[left] + nums[right]
                if total == 0:
                    result.append([nums[first], nums[left], nums[right]])
                    left += 1
                    right -= 1
                    while left < right and nums[left] == nums[left - 1]:
                        left += 1
                    while left < right and nums[right] == nums[right + 1]:
                        right -= 1
                elif ⟦3⟧:
                    left += 1
                else:
                    right -= 1
        return result
""",
            blanks=[dict(a="first > 0 and nums[first] == nums[first - 1]", hint="外层只用一串相同值里的第一次"),
                    dict(a="first + 1, len(nums) - 1", hint="只在固定值右侧找另外两个下标，从剩余区间的两端出发"),
                    dict(a="total < 0", hint="和太小时，把左端换成更大的数")],
        ),
        say="返回的是值三元组而不是下标，所以能先排序。固定一个值后，在它右侧用双指针凑目标和；和小就丢左端，和大就丢右端，因为该端点已经无法与剩余的值配对。外层跳过相同固定值，内层命中后跳过两端重复值。时间 O(n²)，双指针只用常数空间，另计排序和输出空间。",
        trap="别先把输入转成集合，像 [0, 0, 0] 需要三个位置。要保留输入的重复次数，等枚举固定值和内层命中时再跳过重复答案。",
    ),
    "move-zeroes": dict(
        read="把原数组里的零都挪到最后，其他数保持先后顺序，直接修改传入的列表而不返回新表。",
        steps=[
            dict(k="ask", q="判题真正要检查的是哪一项？",
                 options=["传入的列表被改对了，函数返回 None", "函数返回一个新的已整理列表", "把 0 的个数返回给调用者再处理"], answer=0,
                 why="题目要的是对原对象的修改。写 nums = 新列表 只改了函数里的变量指向，调用者手里的列表仍然没变；它也不从返回值读取结果。"),
            dict(k="input", q="哪些元素必须保留原来的相对顺序？",
                 options=["所有非零元素，不论正负", "只保留相邻两个非零元素的顺序", "只保留正数的顺序，负数也一起移到末尾"], answer=0,
                 why="这是稳定地保留非零元素，不是按大小排序，也不是前后两头随便交换。既然要求顺序不变，就按从左到右的出现顺序放置非零值。"),
            dict(k="brute", q="按字面把每个 0 一次次搬到末尾，怎么写、要多慢？",
                 options=["遇零就删除并追加到末尾，只扫未处理区：最坏 O(n²)", "遇零就和最后一个非零数交换：O(n)", "把数组排序后再把零取出：O(n log n)"], answer=0,
                 why="从原位置删掉零再追加，其他数之间的顺序不会动；要标出新追加的尾部，不然会反复搬同一个零。列表中部的删除会搬动后面一大段，最坏每次都要线性时间。"),
            dict(k="waste", q="逐个删零时，哪些元素会被搬很多遍？",
                 options=["这些零后面的非零元素，明明最终只需写到位一次", "已经放在末尾的所有零，每次需要重新计数", "在零前面完全不移动的非零元素"], answer=0,
                 why="例如很多个零之后才出现 1，删前面的每个零都会让 1 左移一格；直接把它写到第一个空位就够了，无需沿路一格一格挪。"),
            dict(k="tool", q="怎样在原数组里直接找到下一个写入位置？",
                 options=["读指针遍历、写指针标记下一个非零位，遇非零就交换", "从右边不断抽出最后一个非零位，和第一个零交换", "用队列存下所有非零元素，最后写回同一个数组"], answer=0,
                 why="写位置等于已经遇到的非零个数，不必另外排队保存。读到非零时，若读写位置不同，写位置一定在已扫到的零区；交换不会打乱其他非零值的先后。"),
            dict(k="state", q="在处理 read 位置之前，数组的哪段已经确定？",
                 options=["[0, write) 是有序保留的非零前缀，[write, read) 全是零", "[0, read) 都是非零，零只可能尚未扫到", "[0, write) 全是零，[write, read) 是已经处理的非零"], answer=0,
                 why="遇零只移动读指针，零区变长；遇非零就交换到 write，再推进 write。处理完最后一格后，已经扫过的区间覆盖整个数组，非零后面就只剩零。"),
        ],
        brute="""class Solution:
    def moveZeroes(self, nums):
        index, end = 0, len(nums)
        while index < end:
            if nums[index] == 0:
                nums.append(nums.pop(index))
                end -= 1
            else:
                index += 1
""",
        cloze=dict(
            code="""class Solution:
    def moveZeroes(self, nums):
        write = 0
        for read, value in enumerate(nums):
            if ⟦1⟧:
                ⟦2⟧
                write += 1
""",
            blanks=[dict(a="value != 0", hint="只让需要保留顺序的元素推进写指针"),
                    dict(a="nums[write], nums[read] = nums[read], nums[write]", hint="把新遇到的非零数放进可写位，同时把零留在后面")],
        ),
        say="原地且顺序不变，所以我用读写两个下标。读指针扫描每一项，写指针之前已经是按原顺序拣出的非零数，写指针到读指针之前是一段零。遇到非零值，就和写指针的位置交换，再推进写指针；遇零只继续读。时间 O(n)、额外空间 O(1)，不需要返回新数组。",
        trap="不能从尾部抽一个非零值来填前面的零，例如 [0, 1, 2] 会变成 [2, 1, 0]。必须按读到非零值的先后依次落位。",
    ),
    "minimum-window-substring": dict(
        read="从字符串 s 里截一段最短的连续片段，把 t 里的每种字符和所需份数都凑齐，找不到就返回空串。",
        steps=[
            dict(k="ask", q="找到最短覆盖窗口后，要交出什么？",
                 options=["窗口对应的原字符串片段，不存在就返回空串", "最短窗口的长度，不存在就返回 0", "把窗口中的字符重新排序，返回排序后的字符串"], answer=0,
                 why="“最短”是挑选标准，输出仍然是子串本身。扫描过程中可以只记起点和长度，最后切片一次，不需要每次发现更短的窗口就复制字符串。"),
            dict(k="input", q="如果 t 是 AAB，窗口里有 A 和 B 就够了吗？",
                 options=["不够，至少两个 A 和一个 B，顺序随意但窗口要连续", "够，覆盖检查只看不同字符是否出现", "不够，两个 A 和一个 B 还必须挨在一起且顺序相同"], answer=0,
                 why="“字符及其次数”让集合不够用，要数每种字符；“连续”限制的是在 s 中截下来的整段，不是要在这段里按顺序匹配 t。"),
            dict(k="brute", q="固定每个左端点后，怎样直接找到该起点最短的覆盖？",
                 options=["为此起点重开计数，从左向右加字符，首次凑齐就停：O(n² + |t|)", "只看长度刚好等于 t 的窗口：O(n + |t|)", "排序后用二分找字符，直接返回更短的排好序片段"], answer=0,
                 why="固定左端后窗口越扩越长，第一个合法的右端就是这个起点的最优解。各起点分别做一遍，最坏每次扫到很靠右的位置，目标计数表只需预先建一次。"),
            dict(k="waste", q="左端点向右挪一格时，怎样省下重新扩张？",
                 options=["保留原窗口其余字符的计数，只减掉被移出的那一份", "把 t 排序，免去每个新起点的字符串比较", "只记录一共见过多少字符，不记录各自是什么"], answer=0,
                 why="相邻起点的候选窗口高度重叠；移掉一个字符只会改变一个计数。并且更小的右端配上更靠右的左端只会覆盖更少，原来没凑齐的右端不值得回头试。"),
            dict(k="tool", q="用什么方法判断何时该扩、何时该缩？",
                 options=["滑动窗口加字符差额表和总缺额，够了就尝试缩左端", "固定长度为 |t| 的滑动窗口，所有窗口都等长", "用集合记录窗口出现的字符，遇齐种类就缩"], answer=0,
                 why="窗口一旦覆盖，就先记答案再缩，试着去掉多余字符；缺了才继续扩。要常数时间判断是否够了，用差额表记每种字符还欠多少，再用一个数维护总欠缺的份数。"),
            dict(k="state", q="设 need[ch] 是目标计数减当前计数，何时更新总缺额？",
                 options=["加入前差额为正就少缺一份；移出后差额为正就多缺一份", "每次加入都少缺一份，每次移出都多缺一份", "只在某字符加入后差额为零时才少缺一份"], answer=0,
                 why="负差额表示有富余。加入时先看它是否原本欠着，移出时则看拿走这一份以后是否变成欠着；缺额等于各字符正差额之和，为零才是真正覆盖。"),
        ],
        brute="""class Solution:
    def minWindow(self, s, t):
        required = Counter(t)
        start, best = 0, len(s) + 1
        for left in range(len(s)):
            counts = Counter()
            missing = len(t)
            for right in range(left, len(s)):
                char = s[right]
                counts[char] += 1
                if counts[char] <= required[char]:
                    missing -= 1
                if missing == 0:
                    if right - left + 1 < best:
                        start, best = left, right - left + 1
                    break
        return s[start:start + best] if best <= len(s) else ""
""",
        cloze=dict(
            code="""class Solution:
    def minWindow(self, s, t):
        need = Counter(t)
        missing = len(t)
        left = start = 0
        best = len(s) + 1
        for right, char in enumerate(s):
            if ⟦1⟧:
                missing -= 1
            need[char] -= 1
            while ⟦2⟧:
                if right - left + 1 < best:
                    start, best = left, right - left + 1
                old = s[left]
                need[old] += 1
                if ⟦3⟧:
                    missing += 1
                left += 1
        return s[start:start + best] if best <= len(s) else ""
""",
            blanks=[dict(a="need[char] > 0", hint="先看这份新字符是不是窗口原本欠的"),
                    dict(a="missing == 0", hint="只要一份都不缺，就记候选并继续尝试缩短"),
                    dict(a="need[old] > 0", hint="减掉一份后，检查它是不是从此不够了")],
        ),
        say="连续子串里找最短覆盖，用可伸缩窗口。差额表存目标次数减窗口次数，总缺额只加总正的部分。右端加入原本缺的字符就减少缺额；凑齐后先更新最短窗口，再移走左端，直到重新出现缺额。两端各走一遍，时间 O(|s| + |t|)，额外空间 O(字符集大小)。",
        trap="不要把总缺额初始化成不同字符数，例如 t 为 AAB 时一开始缺的是三份。收缩也要先记录当前仍然合法的窗口，再移出左端。",
    ),
    "product-of-array-except-self": dict(
        read="为数组每个位置分别算出除自己以外其余所有数的乘积，不许做除法，还要在线性时间内完成。",
        steps=[
            dict(k="ask", q="例如输入 [2, 3, 4]，哪一个是所求结果？",
                 options=["[12, 8, 6]，每格对应原数组同一位置", "24，原数组里所有数的乘积", "[1, 2, 6]，每格只记录左边数的乘积"], answer=0,
                 why="不是求一个总积，而是要按原下标输出 n 个值。每个位置只是排除自身，左右两侧都必须参与，结果也不能打乱原位置。"),
            dict(k="input", q="“除了自己”加上“不能除”在提示怎样拆？",
                 options=["拆成当前位置严格左侧和严格右侧的两段，分别求积", "先算总积，再除以当前位置的值", "每次去掉与当前位置的值相同的所有元素"], answer=0,
                 why="不能靠总积去掉因子，尤其零无法当除数。但按下标排除当前格，就自然留下两段；把两段的积相乘就不用触碰当前因子。"),
            dict(k="brute", q="不用除法，最直接怎样算每一格？",
                 options=["每格扫全表，跳过当前下标后累乘：O(n²)", "乘一遍总积，再对每格做一次除法：O(n)", "所有位置都用一次从左向右的连乘结果：O(n)"], answer=0,
                 why="原地理解题意时，先写一个双循环：对于输出位置 i，内层只排除 j == i。它连有零或重复值也能算对，不过每格都把其他因子乘了一遍。"),
            dict(k="waste", q="相邻两格的乘法有哪些可以复用？",
                 options=["相邻位置的左侧积只差一个因子，右侧积也类似", "每格的乘积都相同，计算第一格就够了", "重复的是乘积里的零，把输入的零删掉就行"], answer=0,
                 why="看严格左边，位置 i + 1 只比位置 i 多乘原数组的第 i 项；严格右边反着扫也有同样关系。把已经算完的一段当成累积量，下一步只需乘新因子。"),
            dict(k="tool", q="线性时间且不多开两个数组，怎么存前后缀乘积？",
                 options=["前缀积先存输出数组，反扫时维护一个滚动后缀积并乘入", "分别完整存前缀和后缀两张表，输出时相加", "把 nums 原地替换成前缀积，再从中直接读原值算后缀积"], answer=0,
                 why="每格只需要自己的左右积。正向扫描先把左积落在输出那一格，反向扫描只需手上当前的右积即可合并；保留原数组用于两次更新累积量。"),
            dict(k="state", q="每轮用当前积更新答案和纳入 nums[i]，谁先谁后？",
                 options=["先给答案用当前积，再把 nums[i] 乘进滚动积", "先乘 nums[i] 再给答案用，保证当前格被算进来", "到达零时把滚动积重置为 1，再写答案"], answer=0,
                 why="处理 i 时，左积只包含小于 i 的下标，右积只包含大于 i 的下标。空的一侧初始是乘法单位元 1；先把 nums[i] 乘进来就会把自己算进去。"),
        ],
        brute="""class Solution:
    def productExceptSelf(self, nums):
        result = []
        for skip in range(len(nums)):
            product = 1
            for index, value in enumerate(nums):
                if index != skip:
                    product *= value
            result.append(product)
        return result
""",
        cloze=dict(
            code="""class Solution:
    def productExceptSelf(self, nums):
        result = [1] * len(nums)
        prefix = 1
        for index, value in enumerate(nums):
            result[index] = prefix
            ⟦1⟧
        suffix = 1
        for index in range(len(nums) - 1, -1, -1):
            result[index] = ⟦2⟧
            ⟦3⟧
        return result
""",
            blanks=[dict(a="prefix *= value", hint="当前因子属于下一格的左边"),
                    dict(a="result[index] * suffix", hint="把已经保存的左边和手里的右边合起来"),
                    dict(a="suffix *= nums[index]", hint="当前因子属于下一轮那一格的右边")],
        ),
        say="不能除法就把每格排除自身后留下的两段分别乘起来。正向扫，把严格左边的积写进输出数组；反向扫，拿严格右边的积乘到这一格。两个滚动积都从 1 开始，每轮先用积再纳入当前元素，零也能自然参与。两遍扫描时间 O(n)，不计输出空间是 O(1)。",
        trap="更新滚动积的顺序不能反。对 [2, 3]，第一格左边什么都没有，左积应该是 1；先乘 2 才写入会把排除的元素加回来。",
    ),
    "search-insert-position": dict(
        read="在严格升序数组里找目标值的下标；找不到就返回能把它插进去且仍然有序的那个位置。",
        steps=[
            dict(k="ask", q="在 [1, 3, 5] 里找 6，返回什么？",
                 options=["3，目标应该插在末尾之后", "-1，因为数组里没有 6", "2，因为 5 是最接近 6 的现有元素"], answer=0,
                 why="输出的是下标或插入位置，不是存在性，也不是最近的值。末尾之后也是合法插入位，因此位置可以等于数组长度。"),
            dict(k="input", q="把“找值”和“找插入位”统一成哪个条件？",
                 options=["找第一个大于等于目标的值的位置，没有则返回长度", "只找第一个比目标严格大的值的位置", "找和目标绝对差最小的值的位置"], answer=0,
                 why="升序意味着较小的值都应在目标左边。第一个不小于目标的值如果相等就是命中，否则在它前面插入；所有值都偏小时就放到最后。"),
            dict(k="brute", q="怎样线性扫描也能同时处理存在和不存在？",
                 options=["从左往右，遇到第一个 >= target 就返回，否则返回长度：O(n)", "扫描到相等才返回，否则返回 -1：O(n)", "先实际插入目标再排序，最后返回旧数组中最接近的位置"], answer=0,
                 why="线性写法直接按统一条件找分界点。它不需要真改数组，在数组头部、内部和尾部插入都能处理，只是最坏要路过所有更小的元素。"),
            dict(k="waste", q="中间位置比目标小时，哪些比较可以跳过？",
                 options=["中间位置及左边全比目标小，不必逐个比较", "只能跳过中间位置，左边仍可能出现目标", "能排除整段右侧，因为右侧比中间位置大"], answer=0,
                 why="利用的是比较结果的单调性：如果中间还不够大，左边一定也不够大；如果中间已经够大，最左的合格位置不会在它右边。"),
            dict(k="tool", q="不用额外数组，怎么快速找“小于”到“不小于”的分界？",
                 options=["二分下界，找首个 >= target 的位置", "普通二分只找相等，失败直接给 -1", "双指针从两端逐格向中间靠近"], answer=0,
                 why="这是找单调真假序列从假转真的地方。每次试中间，一次排除约一半候选；失败不能照搬普通查找的 -1，而要留下两边之间的插入位。"),
            dict(k="state", q="用 lo = 0、hi = len(nums)，中间值够大时留不留 mid？",
                 options=["保留，令 hi = mid，因为 mid 可能正是首个合格位置", "不保留，令 hi = mid - 1，避免重复比较", "把 lo 跳到 mid + 1，既然够大就继续往右找"], answer=0,
                 why="把答案位置夹在闭区间 [lo, hi] 内，允许 hi 先指向末尾之后。mid 不合格才从左边丢掉；合格时它本身不能排除。夹到 lo == hi 就是插入位。"),
        ],
        brute="""class Solution:
    def searchInsert(self, nums, target):
        for index, value in enumerate(nums):
            if value >= target:
                return index
        return len(nums)
""",
        cloze=dict(
            code="""class Solution:
    def searchInsert(self, nums, target):
        lo, hi = 0, len(nums)
        while lo < hi:
            mid = (lo + hi) // 2
            if nums[mid] >= target:
                hi = ⟦1⟧
            else:
                lo = ⟦2⟧
        return lo
""",
            blanks=[dict(a="mid", hint="当前中点够大，仍有可能就是答案"),
                    dict(a="mid + 1", hint="当前中点太小，连它也从候选里排除")],
        ),
        say="有序且找插入位，我把问题改成找第一个不小于目标的下标，找不到就等于数组长度。二分时答案总在 lo 到 hi 之间，包括末尾后一格。如果中点够大，就保留中点当上界；否则中点及左边都不要。两界重合就是结果，时间 O(log n)，额外空间 O(1)。",
        trap="别拿只查是否存在的二分模板照搬 hi = mid - 1。这里 nums[mid] 大于目标时，mid 也可能恰好是插入位置，不能提前扔掉。",
    ),
    "search-in-rotated-sorted-array": dict(
        read="升序数组被从某处切开、把两段对调了，在旋转后的数组里返回目标的下标，找不到就返回 -1。",
        steps=[
            dict(k="ask", q="在 [4, 5, 6, 1, 2, 3] 中找 2，返回什么？",
                 options=["4，目标在旋转后数组里的下标", "1，目标在旋转前数组里的下标", "3，把升序打断的那个位置"], answer=0,
                 why="旋转只是输入具有的结构，不是要输出的结果。要保留现有位置，若先把数组排回升序，就丢掉了题目要返回的下标。"),
            dict(k="input", q="看到“旋转过、没有重复”，二分还能利用什么？",
                 options=["至多一个断点，因此中点分开的两半至少一半是升序的", "数组还是全局升序，只是最小值换了位置", "中点值一定比两个端点都大"], answer=0,
                 why="旋转只把一个从大值回到小值的落差塞进数组；它不能同时落在以 mid 分开的两半里。无重复使得端点值比较能可靠地识别哪半没有跨过断点。"),
            dict(k="brute", q="不分析旋转位置时，最稳的保底是什么？",
                 options=["逐个值和目标比较，命中返回当前下标，否则返回 -1：O(n)", "直接按原始升序数组做标准二分：O(log n)", "排序后找到目标，返回排序后的下标：O(n log n)"], answer=0,
                 why="线性查找不依赖顺序，找到的位置就是原下标。普通二分依赖整个候选区间升序，在断点附近仅比较目标和中点会把正确一侧丢掉。"),
            dict(k="waste", q="知道一半是升序，怎样少做逐一比较？",
                 options=["用这半两端的值判断目标是否可能在里面，一次排除一半", "先找到断点才有任何信息，在此之前只能逐一比较", "只看中点比目标大还是小，就和没旋转时一样"], answer=0,
                 why="有序半边的端点直接给出值域，而旋转数组断点两侧的值域不会交叠。目标在有序半的值域内且存在时只能落在这半；不在其值域就整半排除。"),
            dict(k="tool", q="每轮拿到 mid 后，先判断什么再选边？",
                 options=["先查 mid 是否命中，再用 nums[lo] <= nums[mid] 识别左半是否有序", "先看目标是否比 nums[mid] 小，小就永远去左半", "同时递归搜索中点两半，等一边找到答案"], answer=0,
                 why="如果左端不大于中点，左半没跨断点，且 lo == mid 也算有序；否则右半有序。只检验已知有序的那半的值域，就不需要预先找断点。"),
            dict(k="state", q="mid 已经排除，且左半有序，什么情况下保留左半？",
                 options=["nums[lo] <= target < nums[mid]，令 hi = mid - 1", "target < nums[mid] 就够了，令 hi = mid - 1", "nums[lo] < target <= nums[mid]，令 hi = mid"], answer=0,
                 why="循环维持“若目标存在，一定在闭区间 [lo, hi]”。保留左半时必须包含 lo 的值，而 mid 已经查过就不再留；右半同理，包含 hi 的值。"),
        ],
        brute="""class Solution:
    def search(self, nums, target):
        for index, value in enumerate(nums):
            if value == target:
                return index
        return -1
""",
        cloze=dict(
            code="""class Solution:
    def search(self, nums, target):
        lo, hi = 0, len(nums) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if nums[mid] == target:
                return mid
            if ⟦1⟧:
                if ⟦2⟧:
                    hi = mid - 1
                else:
                    lo = mid + 1
            else:
                if ⟦3⟧:
                    lo = mid + 1
                else:
                    hi = mid - 1
        return -1
""",
            blanks=[dict(a="nums[lo] <= nums[mid]", hint="左端和中点的值能告诉你这一半有没有跨过断点"),
                    dict(a="nums[lo] <= target < nums[mid]", hint="看目标是否在左侧有序值域内，中点已经比较过"),
                    dict(a="nums[mid] < target <= nums[hi]", hint="看目标是否在右侧有序值域内，别漏掉最右端")],
        ),
        say="旋转保留了两段升序，而且只有一个断点。二分时先查中点，再比较左端和中点识别有序的半边；用该半边的端点值判断目标是否可能在里面。每次只留有希望的一半，中点已查过不用保留。时间 O(log n)，额外空间 O(1)。",
        trap="别把左半有序的判断写成 nums[lo] < nums[mid]。只剩两格时 mid 可能就是 lo，这个单元素左半也是有序的。",
    ),
    "daily-temperatures": dict(
        read="对每一天找它之后第一次温度更高的那天，返回相隔的天数，等不到就记为零。",
        steps=[
            dict(k="ask", q="对温度 [70, 71, 90] 的第一天，答案是多少？",
                 options=["1，因为第二天就是第一次升温", "2，因为第三天是后续最热的一天", "71，因为第二天是第一次升温"], answer=0,
                 why="每格输出的是下标差而不是温度。题目要的是“第一次更高”，找到比当天高的最近位置就能定结果，不需要知道后续最高值。"),
            dict(k="input", q="“之后第一个严格更高”给处理顺序什么提示？",
                 options=["从左往右扫，新温度可以给以前还没等到升温的日子结算", "先把温度排序，再把相邻温度相减", "用固定宽度窗口寻找温度最高的一天"], answer=0,
                 why="原下标决定先后和天数，不能排序。反过来想，比起每一天问未来有没有更暖的日子，可以让今天来回答此前所有等它的日子。"),
            dict(k="brute", q="从每一天单独向后找，要付出什么代价？",
                 options=["逐日向后直到第一个更热，最坏 O(n²)", "只比较紧挨的下一天，最坏 O(n)", "在后半段对温度二分，最坏 O(n log n)"], answer=0,
                 why="对每个起点从近到远扫描，第一次严格升温就停。温度全相等时，所有起点都会扫到末尾，且这些温度并不是按搜索所需的顺序排列的。"),
            dict(k="waste", q="今天出现一个高温时，哪些旧扫描能合并？",
                 options=["几个还没找到更高温的旧日子，可由今天一次性结算", "把温度相同的所有日子合并成同一个答案", "只要今天比昨天热，就能结算所有更早的日子"], answer=0,
                 why="例如 [73, 72, 71, 75]，最后一天是前三天共同遇到的第一次升温。没结算的旧温度从早到晚不可能上升，否则较早且较低的那天早已被结算。"),
            dict(k="tool", q="用什么结构维护这些等升温的旧日子？",
                 options=["栈，存待结算的下标，温度从栈底到栈顶非递增", "普通队列，最早等的日子总应该第一个结算", "集合，只存没有被结算过的温度值"], answer=0,
                 why="栈顶温度最低，今天若超过它就可以弹掉并继续问下一个；若连栈顶都不超过，更深处的也不用检查。要算相隔天数，还必须存下标。"),
            dict(k="state", q="今天温度何时弹栈？弹出的旧日子怎么记答案？",
                 options=["今天严格高于栈顶日才弹，填写今天下标减去旧下标", "今天大于等于栈顶日就弹，填写两天温差", "不管温度怎样，每天最多弹一个位置"], answer=0,
                 why="栈里都是没被任何更早高温结算的下标。今天能够弹掉它，今天就是它遇到的第一个严格高温；相等时还得留在栈里继续等。"),
        ],
        brute="""class Solution:
    def dailyTemperatures(self, temperatures):
        result = [0] * len(temperatures)
        for day, temp in enumerate(temperatures):
            for later in range(day + 1, len(temperatures)):
                if temperatures[later] > temp:
                    result[day] = later - day
                    break
        return result
""",
        cloze=dict(
            code="""class Solution:
    def dailyTemperatures(self, temperatures):
        result = [0] * len(temperatures)
        pending = []
        for day, temp in enumerate(temperatures):
            while pending and ⟦1⟧:
                old = pending.pop()
                result[old] = ⟦2⟧
            ⟦3⟧
        return result
""",
            blanks=[dict(a="temp > temperatures[pending[-1]]", hint="今天必须严格超过栈顶那天的温度"),
                    dict(a="day - old", hint="要等几天就是两个下标之差"),
                    dict(a="pending.append(day)", hint="今天也要等将来的升温，先把今天的下标入栈")],
        ),
        say="这是给每个下标找右边第一个更大的值。我从左到右，用单调栈存还没等到升温的下标。今天只要比栈顶那天热，就弹掉并填两天下标差，直到栈顶不少于今天，再把今天入栈。每个位置最多进出栈各一次，时间 O(n)，栈空间 O(n)。",
        trap="相等不算升温。[70, 70, 71] 中两个 70 都该等到 71，答案是 [2, 1, 0]，弹栈条件不能把相等也算进去。",
    ),
    "largest-rectangle-in-histogram": dict(
        read="从柱状图中挑一段连续的柱子，用其中最矮的高度撑起矩形，求能撑起的最大面积。",
        steps=[
            dict(k="ask", q="用高度 [2, 1, 3] 的三根柱子组成一个矩形，面积是多少？",
                 options=["3，最矮柱高 1 乘连续宽度 3", "6，把三根柱子的高度加起来", "9，用最高柱高 3 乘连续宽度 3"], answer=0,
                 why="矩形顶边必须平，不能在矮柱的上方悬空，因此这一段能用的最大高度是最矮值。题目要在所有连续区间中选最大的这个面积，不是柱子面积总和。"),
            dict(k="input", q="把某根柱子当作矩形高度时，什么会挡住它？",
                 options=["向左或向右遇到的首根更矮柱子", "两侧首根更高的柱子", "一根与它等高的柱子，等高不能拼接"], answer=0,
                 why="已固定高度时，扩得越宽面积越大；高柱和等高柱都能给这一高度提供支撑。换个视角，不枚举区间，改为给每个可能的瓶颈高度找能撑多宽。"),
            dict(k="brute", q="用连续区间直接枚举，怎么做到 O(n²)？",
                 options=["固定左端，让右端逐步增加，顺手更新该段最矮值", "固定左端，记到目前最高值，乘每次的宽度", "枚举两端，只比较两根端点柱子的高度"], answer=0,
                 why="右端每多一根，新的最小值只需用旧最小值与新高度比较，免去重扫这段，但左右端点组合仍有 O(n²) 种。中间的矮柱不能忽略。"),
            dict(k="waste", q="一根柱子作为最矮柱时，为何不必试遍每种宽度？",
                 options=["同一最低高度的更窄矩形不会更优，只需要它能撑开的边界", "每种宽度的面积都会相同，只算任意一个就行", "找到全局最矮那根，就不用再看其他候选高度"], answer=0,
                 why="大量区间是在重复试同一个瓶颈高度。若高为 h，在不遇到矮柱的前提下加宽只会让面积不减；找到左右阻挡的位置就能批量省掉那些更窄的尝试。"),
            dict(k="tool", q="扫描时，怎样在遇到矮柱的当下结算之前的高柱？",
                 options=["用高度非递减的下标栈，当前柱比栈顶矮就弹栈计算", "用高度递减的栈，当前柱比栈顶高就结算矮柱", "用最大堆始终取当前最高柱，不保存柱子的位置"], answer=0,
                 why="右边界未知的柱子先压栈；当前高度若连栈顶都不低，栈内更低的也未被挡住。若更低，则可以从最高的待结算柱开始逐一栈顶弹出。"),
            dict(k="state", q="当前下标 i 挡住栈顶，弹出后新栈顶是 j，宽度怎么算？",
                 options=["i - j - 1；两侧边界都不纳入本次矩形", "i - j；把挡住右边的矮柱也纳入", "i - 弹出的下标；矩形只能从被弹出的柱子向右扩"], answer=0,
                 why="弹出时，开区间 (j, i) 内的柱都够高。若 j 与弹出柱等高，本次先只算它右侧，更靠左的等高柱随后弹出会覆盖更宽的范围。空栈可视作 j = -1。"),
        ],
        brute="""class Solution:
    def largestRectangleArea(self, heights):
        best = 0
        for left, height in enumerate(heights):
            lowest = height
            for right in range(left, len(heights)):
                lowest = min(lowest, heights[right])
                best = max(best, lowest * (right - left + 1))
        return best
""",
        cloze=dict(
            code="""class Solution:
    def largestRectangleArea(self, heights):
        stack = [-1]
        best = 0
        for index in range(len(heights) + 1):
            current = heights[index] if index < len(heights) else 0
            while stack[-1] != -1 and ⟦1⟧:
                height = heights[stack.pop()]
                width = ⟦2⟧
                best = max(best, height * width)
            stack.append(index)
        return best
""",
            blanks=[dict(a="heights[stack[-1]] > current", hint="只弹那些被当前矮柱挡住的栈顶柱"),
                    dict(a="index - stack[-1] - 1", hint="用弹出后的新栈顶当左边界，两端都不算进去")],
        ),
        say="任一最优矩形都可把高度取为区间最低柱，因此我用单调栈找每个候选高度能撑多宽。栈里是按高度非递减的下标；遇到更矮的柱就弹并结算，宽度是当前下标减弹出后栈顶再减一。末尾虚拟高度零触发剩余正高柱结算。每根进出栈至多一次，时间和额外空间都是 O(n)。",
        trap="算宽要看弹出之后的新栈顶，而不是被弹出的下标。比如 [2, 2, 1] 遇到 1 时，第一个 2 最终能向右跨过第二个 2，面积是 4。",
    ),
    "top-k-frequent-elements": dict(
        read="数清数组里各个不同值出现了几次，返回频率最高的 k 个值，结果内部不要求顺序。",
        steps=[
            dict(k="ask", q="输入 [5, 5, 5, 9, 9, 20]，k = 2，要交出什么？",
                 options=["值 5 和 9，顺序不限", "频率 3 和 2，按大小排列", "值 20 和 9，因为它们数值最大"], answer=0,
                 why="比较的依据是出现频率，输出的是值本身，而且同一个值只出现一次。“集合唯一”不代表必须按频率排序输出，只代表哪些值入选没有歧义。"),
            dict(k="input", q="长度为 n 的数组里，一个已出现值的频次可能多大？",
                 options=["一定在 1 到 n 之间，与值的正负和大小无关", "一定在 1 到 k 之间，因为只取前 k 个", "由数组中的最大数决定，值越大可能出现得越多"], answer=0,
                 why="关键是用次数做排名：它是小范围的整数，最多 n，而值本身可能很分散。这个范围给了我们不用比较排序也能按频次取数的机会。"),
            dict(k="brute", q="有了频次后，直接按排名筛选怎样写？",
                 options=["计数后把所有不同值按频次排序，再取前 k 个：O(n + u log u)", "把原数组按数值降序排序，然后取前 k 个不同值", "只计数前 k 个不同值，因为后面的值来得太迟"], answer=0,
                 why="先用字典计数，再把 u 个不同值都排出完整名次，是容易写对的保底。计数是必需的，但排序付出了比较所有名次的代价。"),
            dict(k="waste", q="只要前 k 个且不要求结果顺序，全量排名哪里浪费？",
                 options=["不必比较同一频次的值，也不必排落选者之间的相对名次", "可以跳过计数，因为出现很早的值一定更频繁", "只用消除一份输入中的重复值，重复次数不必记"], answer=0,
                 why="次数相同就能放同一组，不需要在组内比谁的值大；低频组如果已经轮不到，甚至不用遍历里面的值。每个频次都有一个现成的整数编号。"),
            dict(k="tool", q="既然频次有界，如何用它直接定位排名的组？",
                 options=["哈希表计数，开频次桶，按频次从大到小取桶中元素", "按原始数值分桶，从最大数值的桶往下取", "维持一个大小为 k 的最大堆，一满就踢掉频次最高的值"], answer=0,
                 why="直接拿频次当桶下标，就不需比较值的排名。小根堆也可只保留 k 个候选；这里频次桶从 1 到 n，连扫空桶算进去仍是线性的，代价是要开桶。"),
            dict(k="state", q="从高频桶往下取时，怎样保证恰好拿 k 个？",
                 options=["每个不同值只入所属频次桶一次，取满 k 个即停", "每出现一次值就放一次，桶里重复值也算进 k 个", "先取完所有非空桶，再按数值大小挑 k 个"], answer=0,
                 why="扫到频次 f 时，所有比 f 高的值都已经领先；单个值只在一个桶里出现一次，因此每取一项，结果长度就增加一个不同值。取满即可交卷。"),
        ],
        brute="""class Solution:
    def topKFrequent(self, nums, k):
        counts = Counter(nums)
        ranked = sorted(counts, key=counts.get, reverse=True)
        return ranked[:k]
""",
        cloze=dict(
            code="""class Solution:
    def topKFrequent(self, nums, k):
        counts = Counter(nums)
        buckets = [[] for _ in range(len(nums) + 1)]
        for value, frequency in counts.items():
            ⟦1⟧
        result = []
        for frequency in ⟦2⟧:
            for value in buckets[frequency]:
                result.append(value)
                if len(result) == k:
                    return result
""",
            blanks=[dict(a="buckets[frequency].append(value)", hint="用频次做桶下标，但放进桶里的是值"),
                    dict(a="range(len(nums), 0, -1)", hint="最高可能频次是数组长度，从大到小取")],
        ),
        say="先用哈希表记每个值的次数。频次是 1 到 n 的整数，而且只要前 k 个值，不用完整排序。我按频次分桶，每个值只进自己的桶，从最高频往下取，到 k 个立即停。计数、装桶和扫描合起来时间 O(n)，字典和桶的额外空间 O(n)。",
        trap="桶下标是频次，但桶里的内容是原值，不能把频次当答案。若数组全是同一个数，其频次恰好等于数组长度，所以需要 n + 1 个桶。",
    ),
    "reverse-linked-list": dict(
        read="把单链表上的每一条 next 的方向反过来，返回原来的尾节点作为新头；空链表仍返回空。",
        steps=[
            dict(k="ask", q="反转 1 → 2 → 3 后，返回哪一个节点？",
                 options=["原来的 3，它是新链表的头", "原来的 1，头节点变量应一直不变", "值列表 [3, 2, 1]，不必改节点的 next"], answer=0,
                 why="输出的是链表头，不是倒序打印值。原来的尾节点现在要能沿着 next 走到原来的头，原头的 next 则必须成为空。"),
            dict(k="input", q="单链表最关键的限制是什么？",
                 options=["节点只能沿 next 往后走，覆盖它前得保住后续入口", "每个节点都自带上一个节点的地址", "能像数组一样用下标直接取任意节点"], answer=0,
                 why="如果直接改掉 cur.next，单链表没有后退再绕回去的路。要边走边改，就要先把原来指向的后一个节点存起来。"),
            dict(k="brute", q="不边遍历边改，用额外空间怎样先写一个正确方案？",
                 options=["把节点逐个存进列表，再按逆序连回去：时间和空间均 O(n)", "只把值放进列表并返回倒序值列表：O(n)", "从头开始按前进顺序直接改 next，不保存原后继"], answer=0,
                 why="列表把每个节点的引用都留了下来，反向重接时不会弄丢节点。它很好理解，代价是保存整条链的引用并分两轮处理。"),
            dict(k="waste", q="反过来连当前节点时，真的要记住全部节点吗？",
                 options=["不必，只要已反转部分的头，以及当前节点原来的下一个", "必须记住每个节点原下标才能算反转方向", "不必，只用记一个原链表头，能从改好的链接找回未处理部分"], answer=0,
                 why="已处理的节点可以自己用 next 串起来，没处理的部分也还保留原来的 next。两段之间只缺极少的指针，不需要单独存每个地址。"),
            dict(k="tool", q="边扫边改时，用哪几个指针？",
                 options=["prev 指已反转部分的头，cur 指下一待处理节点，另存 nxt", "只用 cur，改完 cur.next 后继续沿新的 next 走", "把头尾节点的值两两交换，但 next 不变"], answer=0,
                 why="把当前节点接到 prev 上，再把它升级成已反转部分的新头。nxt 像临时书签，让改链后还能跳到未处理的那部分继续。"),
            dict(k="state", q="保存 nxt 后，怎样更新反转链与未处理链的两个入口？",
                 options=["cur.next 指向 prev，再让 prev = cur、cur = nxt", "先让 cur = nxt，再把 cur.next 接到 prev", "让 prev.next 指向 cur，再让 cur 指向自己的 next"], answer=0,
                 why="每轮开始 prev 是已经反转好的头，cur 是还没反转的头。先把 cur 接过来，再同步移动两个入口；cur 为空时，prev 正好是完整新链的头。"),
        ],
        brute="""class Solution:
    def reverseList(self, head):
        nodes = []
        current = head
        while current:
            nodes.append(current)
            current = current.next
        if not nodes:
            return None
        for index in range(len(nodes) - 1, 0, -1):
            nodes[index].next = nodes[index - 1]
        nodes[0].next = None
        return nodes[-1]
""",
        cloze=dict(
            code="""class Solution:
    def reverseList(self, head):
        prev, cur = None, head
        while cur:
            nxt = ⟦1⟧
            ⟦2⟧
            prev, cur = ⟦3⟧
        return prev
""",
            blanks=[dict(a="cur.next", hint="先保存未处理部分接下来的入口"),
                    dict(a="cur.next = prev", hint="把当前节点接到已经翻好的那一段上"),
                    dict(a="cur, nxt", hint="已处理链的头变为当前节点，未处理链从原后继开始")],
        ),
        say="单链表反转是改 next，不是倒序打印。我把链表分成已反转和未处理两段，用 prev、cur 指向两个段头。每轮先保存 cur 的原后继，再让它指向 prev，最后把两个段头各往前推进一步。未处理链为空就返回 prev，时间 O(n)，额外空间 O(1)。",
        trap="先保存旧的 cur.next，再覆盖它。举例 1 → 2 → 3，第一步若先令 1.next = None，就失去了从 1 找到 2 的机会。",
    ),
    "remove-nth-node-from-end-of-list": dict(
        read="在单链表里删掉从尾巴往前数第 n 个节点，返回剩余链表的头，原头也可能被删。",
        steps=[
            dict(k="ask", q="如果链表只有一个节点，且 n = 1，应返回什么？",
                 options=["空头指针，因为唯一的节点被删除", "被删掉的节点，调用者自行清理", "原来的头节点，但把它的值清零"], answer=0,
                 why="返回的是删除后链表的头，不是删除的元素。即便节点值一样，题目也按位置删除；删的是原头时，返回值必须随之变化。"),
            dict(k="input", q="“倒数第 n 个”遇上单链表，哪里不方便？",
                 options=["只能从头向尾走，且删除还需要找到目标的前一个节点", "可以从尾向前直接走 n 步，只是找不到节点值", "只要找到了目标本身，就能处理包括删尾在内的所有情况"], answer=0,
                 why="单链表没有 prev，要让前驱的 next 跳过目标，就得提前掌握前驱的位置。删头没有真正前驱，可以人为造一个在头前的虚拟节点。"),
            dict(k="brute", q="不知道长度时，怎样用两趟扫描先写出正确解？",
                 options=["先数长度 L，再从虚拟头走 L - n 步到目标前驱：O(L)", "先走 n 步，再在那个位置删掉节点：O(n)", "从尾巴倒着走 n 步后直接断链：O(n)"], answer=0,
                 why="倒数第 n 个是正数第 L - n + 1 个；虚拟头是第 0 个，走 L - n 步刚好停在前驱。两趟仍是线性，只是第一趟走到尾才知道该停在什么位置。"),
            dict(k="waste", q="能否在第一次向尾巴走时，就开始定位前驱？",
                 options=["可以，让另一个指针一直落后探路指针 n 步", "不行，必须先算出链表全长才能移动另一个指针", "可以，每走一步就从头重新数 n 个节点"], answer=0,
                 why="长度只是找相对距离的中间结果。若快指针恰好比慢指针领先 n 条边，到尾时慢指针已知离尾 n 步，正好在目标前一格，不用回头重扫。"),
            dict(k="tool", q="要统一删头和删中间，两个指针从哪里开始？",
                 options=["都从虚拟头开始，先让快指针走 n 步，再两者一起走", "都从原头开始，慢指针到哪里就把那个节点删掉", "快指针每次走两步、慢指针走一步，用相遇位置删除"], answer=0,
                 why="这里不是找中点或判环，关键是固定相隔 n 步而非固定速度比。虚拟头让慢指针也能停在原头之前，删除操作始终是同一句。"),
            dict(k="state", q="快慢指针从虚拟头起步且相隔 n 步，快指针何时停？",
                 options=["停在最后一个真实节点，慢指针的 next 就是要删的", "停在尾后的 None，慢指针的 next 就是要删的", "快慢指针相遇时停，删慢指针当前节点"], answer=0,
                 why="把尾节点当倒数第 1 个，距它前面 n 步的是倒数第 n + 1 个位置（可能是虚拟头），即目标前驱。如果快指针再走到 None，慢指针会多走一格。"),
        ],
        brute="""class Solution:
    def removeNthFromEnd(self, head, n):
        size = 0
        current = head
        while current:
            size += 1
            current = current.next
        dummy = ListNode(0, head)
        before = dummy
        for step in range(size - n):
            before = before.next
        before.next = before.next.next
        return dummy.next
""",
        cloze=dict(
            code="""class Solution:
    def removeNthFromEnd(self, head, n):
        dummy = ListNode(0, head)
        fast = slow = dummy
        for step in range(⟦1⟧):
            fast = fast.next
        while ⟦2⟧:
            fast = fast.next
            slow = slow.next
        ⟦3⟧
        return dummy.next
""",
            blanks=[dict(a="n", hint="用快指针领先的步数编码倒数的位置"),
                    dict(a="fast.next", hint="有后继才继续，快指针要停在最后一个真实节点"),
                    dict(a="slow.next = slow.next.next", hint="慢指针是前驱，从它的 next 跳过目标")],
        ),
        say="要删倒数第 n 个，实际上要让指针停在它的前驱。我加虚拟头，让快指针先走 n 步，再和慢指针同速走。快指针到尾节点时，慢指针离尾 n 步，令它的 next 跳过目标就行，最后返回虚拟头的 next。一次向前扫，时间 O(L)，空间 O(1)。",
        trap="要把快指针停在尾节点，不是尾后的空指针。尤其 n 等于链长时，慢指针应当停在虚拟头，才能正确删去原头。",
    ),
    "binary-tree-level-order-traversal": dict(
        read="从上往下逐层读二叉树，每层由左至右收集节点值，各层单独放一个列表；空树返回空列表。",
        steps=[
            dict(k="ask", q="根为 1、左右子节点为 2 和 3，该返回什么？",
                 options=["[[1], [2, 3]]，同层节点放在一起", "[1, 2, 3]，只要先后顺序对就行", "[[1, 2], [1, 3]]，把每条根到叶的路径列出来"], answer=0,
                 why="层序的先后还不够，结果保留每层的边界。两条路径可以同属一个层的不同位置，不能用根到叶的分组替代按深度分组。"),
            dict(k="input", q="“同层”在树上等价于节点共享什么属性？",
                 options=["离根的边数相同，同层按父节点和左右孩子顺序排列", "父节点一定是同一个节点", "子树高度相同，即离最深叶子的距离一样"], answer=0,
                 why="同层看的是离根的深度，不是离叶子的高度。同层节点的父节点在上一层；按父节点从左到右的顺序加入各自的左、右孩子，就能得到下一层顺序。"),
            dict(k="brute", q="如果一次只想取一层，怎样用最直接的写法？",
                 options=["对每个深度重新从根搜索，收集到该深度的值：最坏 O(n²)", "一直按中序遍历，值变大时就切分到下一层", "每层只跟随最左子节点，遇到空返回前一层"], answer=0,
                 why="对指定深度用先左后右的搜索，能正确收集整层；直到某一深度没有节点。链形树有 n 层，从根重复走到每层需 1 + 2 + …… + n 步。"),
            dict(k="waste", q="每个深度重走一次，真正重复走的是哪里？",
                 options=["从根走到尚未到达目标深度的祖先路径", "重复把每个节点的值放进了每一层答案", "每层内部的节点都做了一次按值排序"], answer=0,
                 why="某层处理完后，下一层的入口就是这层各节点的孩子。把这些孩子直接保留下来，下一次就可以从它们开始，不需要重新从根走路径。"),
            dict(k="tool", q="怎样让下一层入口自动留到当前层之后处理？",
                 options=["广度优先搜索，用队列按先入先出保存节点", "用栈按先入后出，入栈的孩子比同层节点先取出", "用最小堆按节点值排序，较小的先输出"], answer=0,
                 why="先到队列的是当前层，后加的孩子排在尾部，不会插队。先入左孩子再入右孩子能保留题目要求的同层顺序，不依赖节点的值。"),
            dict(k="state", q="一轮处理当前层时，用哪个数决定弹多少次？",
                 options=["在这一轮开始时记下队列长度，只弹出这么多次", "一直弹到队列完全为空，孩子也算当前层", "每处理一个节点后重新读队列长度，当作剩余本层节点数"], answer=0,
                 why="这一轮开始时队列恰好装着本层。处理中会加下一层的孩子，实时长度不再代表本层剩余数量；固定弹出初始数量，结束时队列就只剩下一层。"),
        ],
        brute="""class Solution:
    def levelOrder(self, root):
        if not root:
            return []
        result = []
        target = 0
        while True:
            values = []
            stack = [(root, 0)]
            while stack:
                node, depth = stack.pop()
                if depth == target:
                    values.append(node.val)
                else:
                    if node.right:
                        stack.append((node.right, depth + 1))
                    if node.left:
                        stack.append((node.left, depth + 1))
            if not values:
                return result
            result.append(values)
            target += 1
""",
        cloze=dict(
            code="""class Solution:
    def levelOrder(self, root):
        if not root:
            return []
        queue = deque([root])
        result = []
        while queue:
            values = []
            for step in range(⟦1⟧):
                node = ⟦2⟧
                values.append(node.val)
                if node.left:
                    queue.append(node.left)
                if node.right:
                    queue.append(node.right)
            result.append(values)
        return result
""",
            blanks=[dict(a="len(queue)", hint="取尚未加入任何孩子之时的队列大小"),
                    dict(a="queue.popleft()", hint="较早入队的本层节点必须先出队")],
        ),
        say="要求从上到下按层、同层从左到右，适合用队列做广度优先。每轮开始队列只装本层，我固定这一刻的队列长度，弹出这么多节点取值，并依次推入左、右孩子。结束时队列自然只剩下一层。时间 O(n)，不计输出的空间 O(最大层宽)。",
        trap="处理一层不能直接用 while queue 作为内层循环，因为每次入队的孩子会被接着处理，结果成了一个扁平大层。要先固定当前层的节点数。",
    ),
    "diameter-of-binary-tree": dict(
        read="在树里挑两个节点，沿父子边走它们之间的路径，返回所有这种路径中最大的边数。",
        steps=[
            dict(k="ask", q="单节点树的直径是多少？",
                 options=["0，路径虽然有一个节点，但没有边", "1，因为最长路径经过了一个节点", "取决于节点里存的值"], answer=0,
                 why="要数的是父子连接，不是路径经过的节点个数，也与节点值无关。一条经过 k 个节点的路径恰好有 k - 1 条边。"),
            dict(k="input", q="任意两节点的路径，在树上有什么共同结构？",
                 options=["各条路径都有一个最高点：两端的最近公共祖先", "所有路径都一定经过整棵树的根", "每条路径的端点必须是同一层的两个叶子"], answer=0,
                 why="从一个端点往上爬再往下走，拐弯处就是路径最高点，也可能正好是某一端。如果把它固定下来，两侧最长的路就能独立从左右孩子下面去找。"),
            dict(k="brute", q="把每个节点都当一次最高点，如何直接求答案？",
                 options=["每次独立遍历左右子树求高度，再相加：最坏 O(n²)", "只算根节点左右高度相加：O(n)", "对每个节点只数直接孩子个数，取最大值：O(n)"], answer=0,
                 why="枚举所有最高点可以覆盖不经过根的路径；对每一边，选最深的端点就能让那条臂最长。但链形树上每个节点都会重新数下面几乎同一段链。"),
            dict(k="waste", q="子树高度在哪些地方一遍遍求了？",
                 options=["给不同祖先算最长臂时，会重复进入同一棵后代子树", "相同节点值的高度必定相同，只需按节点值去重", "每次算直径都要反复比较节点值的大小"], answer=0,
                 why="只要某个子树的高度算好了，父节点就能拿它当输入，当场求自己的高度并继续传上去。没必要让每个祖先重新深入那棵子树。"),
            dict(k="tool", q="既要汇报高度，又要更新直径，按什么顺序走树？",
                 options=["后序遍历：先算两个孩子的高度，再处理父节点", "先序遍历：一进父节点就用两个孩子尚未计算的高度", "层序遍历：直接拿整棵树最大深度当直径"], answer=0,
                 why="父节点需要两份孩子结果，先处理孩子最自然。可以递归，也可以用栈标记“孩子处理后再回来”；回来时两个高度都已经能读到。"),
            dict(k="state", q="若空树高度为 0，左右孩子高度为 left 和 right，父节点怎样计算？",
                 options=["用 left + right 更新直径，向上交 1 + max(left, right)", "用 1 + left + right 更新直径，也将这个和向上交", "用 max(left, right) 更新直径，向上交 left + right"], answer=0,
                 why="孩子的高度数该子树下行路径的节点数，接上当前父节点后正好等于那条臂的边数。两臂可组成一条直径候选；交给父节点延长时却只能选一条臂，不能往两侧分叉。"),
        ],
        brute="""class Solution:
    def diameterOfBinaryTree(self, root):
        def height(node):
            deepest = 0
            stack = [(node, 1)] if node else []
            while stack:
                current, depth = stack.pop()
                deepest = max(deepest, depth)
                if current.left:
                    stack.append((current.left, depth + 1))
                if current.right:
                    stack.append((current.right, depth + 1))
            return deepest

        best = 0
        pending = [root] if root else []
        while pending:
            node = pending.pop()
            best = max(best, height(node.left) + height(node.right))
            if node.left:
                pending.append(node.left)
            if node.right:
                pending.append(node.right)
        return best
""",
        cloze=dict(
            code="""class Solution:
    def diameterOfBinaryTree(self, root):
        stack = [(root, False)]
        heights = {}
        best = 0
        while stack:
            node, ready = stack.pop()
            if not node:
                continue
            if not ready:
                stack.append((node, True))
                stack.append((node.right, False))
                stack.append((node.left, False))
            else:
                left = heights.pop(node.left, 0)
                right = heights.pop(node.right, 0)
                best = max(best, ⟦1⟧)
                heights[node] = ⟦2⟧
        return best
""",
            blanks=[dict(a="left + right", hint="以这个节点为最高点，左右两条臂拼起来有多少条边？"),
                    dict(a="1 + max(left, right)", hint="父节点只能沿一条臂延伸，记最长臂再加当前节点")],
        ),
        say="路径未必过根，但都有一个最高点，我对每个节点检查经过它的两条最长下行臂。用显式栈做后序遍历，等两边高度就绪后，用两高度之和更新直径，只把较大高度加一交给父节点。子节点结果用完即丢，时间 O(n)，额外空间 O(树高)。",
        trap="两条臂拼出的路径只用于更新全局答案，不能原样交给父节点：父节点沿一条向下路径只能选其中一臂。单节点树的直径是 0 条边。",
    ),
    "rotting-oranges": dict(
        read="烂橘子每分钟让上下左右的新鲜橘子变烂，求全变烂的时间，只要剩下一个无法感染就返回 -1。",
        steps=[
            dict(k="ask", q="只剩一个新鲜橘子永远碰不到感染，应返回什么？",
                 options=["-1，即使其他橘子都已烂掉", "已经发生过的感染总数", "最后一次成功感染的分钟数"], answer=0,
                 why="求的是“全部”的时间，不是传播多久就结束。除了计时，还得知道传播后有没有剩余新鲜橘子；一开始就没有新鲜橘子则需要零分钟。"),
            dict(k="input", q="多个初始烂橘子在第 0 分钟如何行动？",
                 options=["它们是同时开始的多个源，每次传播只跨一条相邻边", "一次只允许一个源传播，等它结束再启动下一个", "对一个源做递归，能走到的橘子这一分钟全烂"], answer=0,
                 why="“每分钟向四邻感染”就是无权网格图上走一步。某个橘子首次感染用的时间等于离任一源的最短步数，空格不是可通过的中继。"),
            dict(k="brute", q="直接按分钟模拟，怎样避免一轮感染传得太远？",
                 options=["每分钟全图扫描，先收集本轮新感染，扫完再统一改状态", "从左到右扫，发现新感染就立刻让它在本轮传染下一格", "单独模拟每个腐烂源，把各自耗时相加"], answer=0,
                 why="如果发现感染就立刻让它继续传播，扫描先后会改变本轮结果。分收集、提交两步可保留同时传播的题意，扫描时间最坏 O((T + 1) × 行数 × 列数)，T 是成功扩散的轮数。"),
            dict(k="waste", q="每分钟重扫全图时，哪些起点没必要再查？",
                 options=["已经传播过的烂橘子，其邻格以后不会重新变成新鲜", "刚发现的烂橘子，它们还不能在后续分钟参与传播", "所有离第一个源较远的烂橘子，它们一定会晚一些开始"], answer=0,
                 why="感染只会从新鲜变烂，旧腐烂点早就尝试过所有邻格。下分钟只让这一分钟新烂的橘子扩散即可，无需再次查看远处的空格或旧源。"),
            dict(k="tool", q="用什么结构保住每一分钟的传播边界？",
                 options=["多源广度优先，用队列同时放进所有初始烂橘子，再分层扩散", "单源广搜，只从第一个初始烂橘子开始", "递归深搜，每走到更深一层就将全局分钟加一"], answer=0,
                 why="初始腐烂点都是第 0 层；它们发现的首批新邻居进入第 1 层。按层推进天然给出最早感染时间，不会把并行发生的传播当成串行。"),
            dict(k="state", q="新鲜橘子被发现时，何时标记变烂并减剩余数？",
                 options=["当它首次入队就标记并减一，本轮末才会开始处理它", "等它出队时再标记，其他邻居可重复把它加入队列", "每有一个腐烂邻居就减一，不必在网格记录本格状态"], answer=0,
                 why="两个同层的源可能同时看到同一新鲜橘子；入队就标记，第二个源便不会重复计算。当前轮按入轮时的队列大小只处理旧队首，新加入的都等下一轮。"),
        ],
        brute="""class Solution:
    def orangesRotting(self, grid):
        rows, cols = len(grid), len(grid[0])
        minutes = 0
        while True:
            newly_rotten = []
            for row in range(rows):
                for col in range(cols):
                    if grid[row][col] != 1:
                        continue
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        rr, cc = row + dr, col + dc
                        if 0 <= rr < rows and 0 <= cc < cols and grid[rr][cc] == 2:
                            newly_rotten.append((row, col))
                            break
            if not newly_rotten:
                return -1 if any(1 in line for line in grid) else minutes
            for row, col in newly_rotten:
                grid[row][col] = 2
            minutes += 1
""",
        cloze=dict(
            code="""class Solution:
    def orangesRotting(self, grid):
        rows, cols = len(grid), len(grid[0])
        queue = deque()
        fresh = 0
        for row in range(rows):
            for col in range(cols):
                if grid[row][col] == 2:
                    queue.append((row, col))
                elif grid[row][col] == 1:
                    fresh += 1
        minutes = 0
        while ⟦1⟧:
            for step in range(⟦2⟧):
                row, col = queue.popleft()
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rr, cc = row + dr, col + dc
                    if 0 <= rr < rows and 0 <= cc < cols and ⟦3⟧:
                        grid[rr][cc] = 2
                        fresh -= 1
                        queue.append((rr, cc))
            minutes += 1
        return minutes if fresh == 0 else -1
""",
            blanks=[dict(a="queue and fresh", hint="还有感染源，且还有新鲜橘子时才需要再过一分钟"),
                    dict(a="len(queue)", hint="固定本层数量，避免这一轮处理刚感染的橘子"),
                    dict(a="grid[rr][cc] == 1", hint="只有相邻的新鲜橘子才会被感染")],
        ),
        say="每一分钟传播到四邻，相当于图上的一步。我把所有初始烂橘子一并入队做多源广搜，每轮固定处理队列当前这一层，新鲜邻居入队时即标腐烂并扣数量。计到没有新鲜橘子就结束，若队列耗尽仍有剩余则返回 -1。时间和最坏空间都是 O(网格格数)。",
        trap="新感染的一格同一分钟不能继续向外传。用进入本轮时的队列长度划定边界，并在入队时标腐烂，避免两侧同时传来时重复扣数。",
    ),
    "number-of-provinces": dict(
        read="把能直接或经其他城市互相到达的城市归进同一组，最后返回这样的城市组有多少个。",
        steps=[
            dict(k="ask", q="A 连 B、B 连 C，A 不直连 C，算几个省？",
                 options=["一个，三城通过中间点也能互相到达", "两个，只按有直接边的城市对分组", "三个，每个城市都要作为起点计一次"], answer=0,
                 why="输出是组的数量而不是道路数。“直接或间接”允许借别的城市转一手，所以这些边一起把三个点放进了同一连通块。"),
            dict(k="input", q="矩阵里值为 1 和对称，分别表示什么？",
                 options=["i 与 j 有直接连接，且可从任一方走到另一方", "i 必须先于 j 访问，矩阵描述的是前置依赖", "i 与 j 只要间接可达，矩阵里就必定提前填好了 1"], answer=0,
                 why="一行就列出了某城的所有直接邻居；对称说明这是无向图。从一个城市顺着行中的 1 往外找，才能确定整组间接相连的城市。"),
            dict(k="brute", q="不用队列，怎样用整表扫描逐轮凑出一个省？",
                 options=["从一个未归组城市起，反复把已入组者的邻居加入，直到不变：最坏 O(n³)", "数矩阵下三角里有多少个 1，当作总省份数：O(n²)", "对每座城只扫描一次自己的行，有邻居就算一个新省"], answer=0,
                 why="从起点不断扩展，组不再增长时就没有新的可达城市；再从未归组者开始。每轮最多扫 n² 项，每个省的轮数至多与加入的城市数同阶，总计最坏 O(n³)。"),
            dict(k="waste", q="逐轮全表扩展时，哪些行反复看却不会带来新信息？",
                 options=["早已处理过的入组城市的行，它的所有邻居当时就被加入了", "新归组的城市的行，因为它与起点并不一定直连", "矩阵主对角线以外的行，因为自己与自己连通就足够了"], answer=0,
                 why="要继续向外发现新城，只须处理新加入的城市；已经看过的那些邻接行不用再查。给新城市排个待处理清单，就能只读每一行一次。"),
            dict(k="tool", q="怎样用队列扫完一个连通块，再统计下一个？",
                 options=["遍历城市，遇未访问城市就计一个省，并从它广搜全部可达邻居", "只从城市 0 广搜，把没扫到的城全部算成同一个省", "同时将所有城市加入队列，遇到邻接边就加一个省"], answer=0,
                 why="从未访问城开始才意味着找到新的一组；若它和旧组能连通，旧组搜索时早就该把它发现了。计数写在启动搜索的位置，不写在每次发现邻居的位置。"),
            dict(k="state", q="城市什么时候标已访问，一个队列中都是什么？",
                 options=["入队即标记；队列始终是当前省中已发现但尚未扫行的城市", "出队才标记；入队时允许同一个城市排很多次", "每搜完一个省就清空已访问标记，再从下一个下标试"], answer=0,
                 why="对称矩阵会让边能来回走，还有主对角线上的自环。入队就锁定归组，能阻止重复排队；整个外层循环都保留访问记录，才不会把旧省重算。"),
        ],
        brute="""class Solution:
    def findCircleNum(self, isConnected):
        assigned = set()
        provinces = 0
        for start in range(len(isConnected)):
            if start in assigned:
                continue
            group = {start}
            while True:
                size = len(group)
                for city, row in enumerate(isConnected):
                    if city in group:
                        for neighbor, linked in enumerate(row):
                            if linked:
                                group.add(neighbor)
                if len(group) == size:
                    break
            assigned.update(group)
            provinces += 1
        return provinces
""",
        cloze=dict(
            code="""class Solution:
    def findCircleNum(self, isConnected):
        visited = [False] * len(isConnected)
        provinces = 0
        for start in range(len(isConnected)):
            if ⟦1⟧:
                continue
            provinces += 1
            queue = deque([start])
            visited[start] = True
            while queue:
                city = queue.popleft()
                for neighbor, linked in enumerate(isConnected[city]):
                    if ⟦2⟧:
                        visited[neighbor] = True
                        queue.append(neighbor)
        return provinces
""",
            blanks=[dict(a="visited[start]", hint="已被任何一轮搜到的起点不能再多算一个省"),
                    dict(a="linked and not visited[neighbor]", hint="只发现有直接边、且之前没入队的邻居")],
        ),
        say="连通矩阵对称，直接或间接连通就是无向图的一个连通块。我依次检查城市，只有未访问的城市才新计一个省，从它用队列搜完一组。邻居在入队时标记，保证每城的邻接行只查一次。因此矩阵输入的时间 O(n²)，额外空间 O(n)。",
        trap="答案只在启动一次新广搜时加一，而不是每遇到一条边就加一。比如三座城市由两条边连成一串，仍只有一个省。",
    ),
    "permutations": dict(
        read="把互不相同的所有数字各用一次，列出它们能排成的每种顺序，答案内部先列哪种都可以。",
        steps=[
            dict(k="ask", q="[1, 2] 和 [2, 1] 是不是应该各输出一次？",
                 options=["是，排列区分每个位置的先后，而且要返回每一种", "否，两个排列用同一组数，只输出一次", "不用输出列表，只返回排列总数 2"], answer=0,
                 why="排列和组合的区别是同一批元素换顺序就是不同方案。题面说“所有”，不能只求 n! 或在找到第一个合法序列时就停止。"),
            dict(k="input", q="已经放了几个数后，下一格能选什么？",
                 options=["任何还没用过的位置上的数，和原下标先后无关", "只能选比上一个已选数字大的数", "只能选原下标在上一个已选位置右侧的数"], answer=0,
                 why="输入元素互不相同，每个下标只能用一次，但没有原顺序约束。如果总是从上一个位置之后选，那枚举出来的是子序列或组合，漏掉倒序排列。"),
            dict(k="brute", q="先把每格都当成独立选择，再事后检查，要多慢？",
                 options=["生成 n 格、每格有 n 种选择的序列，再用集合查重：O(n × nⁿ)", "先排序，只把首尾交换一次就能列全所有顺序：O(n)", "枚举所有子集并保持原顺序，就能遍历所有排列：O(n × 2ⁿ)"], answer=0,
                 why="每个有效排列都在这 nⁿ 个序列里，只是多数候选重复用了某个数。逐个生成并检查它们确实能得到答案，可是验证到最后一格已经太晚。"),
            dict(k="waste", q="假如前两格都放了 1，后面还需要继续枚举吗？",
                 options=["不需要，重复一旦出现，之后填什么也无法修好", "需要，后面的未用数字可以抵消前面的重复", "只要最后一格不重复，该序列仍是合法排列"], answer=0,
                 why="重复是不可恢复的前缀错误。与其走到叶子才扔掉，不如选择时就不进入重复分支；这样留下的每个前缀都可以补成至少一个结果。"),
            dict(k="tool", q="怎样试完一条排列后再回到其他选择？",
                 options=["递归回溯，用 path 保存已选顺序，用 used 标哪些位置被占", "用全局集合记录所有曾经用过的值，以后永不再用", "用堆每次拿剩下最小值，拼成一条序列就结束"], answer=0,
                 why="path 到第几格就是递归深度，used 只说当前路径占了哪些数字。回溯回来撤销选择，其他分支仍可以用那个数字，只是安排在不同位置。"),
            dict(k="state", q="递归完成一条路后，保存答案和恢复状态怎么做？",
                 options=["叶子存 path 的拷贝；每次返回撤掉刚加的值并清对应占用标记", "叶子直接存 path 引用；回退只弹出最后一个数", "叶子存一份拷贝，但所有用过的位置永久标记"], answer=0,
                 why="path 和 used 在各递归分支间共享，必须一起恢复到进入分支前的样子。答案需要快照，否则回溯不断清空同一个列表，已经加入的结果也会被改掉。"),
        ],
        brute="""class Solution:
    def permute(self, nums):
        result = []
        for sequence in itertools.product(nums, repeat=len(nums)):
            if len(set(sequence)) == len(nums):
                result.append(list(sequence))
        return result
""",
        cloze=dict(
            code="""class Solution:
    def permute(self, nums):
        result, path = [], []
        used = [False] * len(nums)

        def backtrack():
            if len(path) == len(nums):
                result.append(⟦1⟧)
                return
            for index, value in enumerate(nums):
                if ⟦2⟧:
                    continue
                used[index] = True
                path.append(value)
                backtrack()
                path.pop()
                ⟦3⟧

        backtrack()
        return result
""",
            blanks=[dict(a="path[:]", hint="存当前路径的快照，后续弹出时不能改变答案"),
                    dict(a="used[index]", hint="只能选当前路径中还没用过的下标"),
                    dict(a="used[index] = False", hint="撤销刚才占用的下标，留给同层的其他分支")],
        ),
        say="要列出所有不同顺序，适合按位置回溯。path 放已经填好的前缀，used 标记前缀占用的下标；每层选择一个未用数，填满就复制到答案，返回时恢复路径和占用标记。共有 n! 个答案，时间 O(n × n!)，不计输出的额外空间 O(n)。",
        trap="别把同一个 path 对象直接放进结果，回溯的 pop 会同时改掉已经保存的答案。用 path[:] 拍一份快照，再正常撤销选择。",
    ),
    "generate-parentheses": dict(
        read="用恰好 n 个左括号和 n 个右括号，列出所有能按先开后关正确配对的字符串。",
        steps=[
            dict(k="ask", q="最后要返回什么？",
                 options=["每个合法括号字符串组成的列表", "所有合法串的总数", "一个嵌套最深的合法串"], answer=0,
                 why="题目问“所有字符串”，只用公式算个数不够，找到一个合法串也不能马上停。要设计能逐个构造、且不重复的过程。"),
            dict(k="input", q="左右括号总数相等，为什么仍可能不合法？",
                 options=["任何前缀都不能关掉比已经打开的更多括号，例如 )(", "只要总数相等就合法，与前缀无关", "每个左括号后面必须立刻跟一个右括号"], answer=0,
                 why="把左括号当打开一扇门、右括号当关闭最后打开的门。若读到某个前缀时已经关闭过多，靠后面再打开不能补救；但嵌套是允许的。"),
            dict(k="brute", q="先生成全部可能串，再检查合法性，要多少时间？",
                 options=["2n 个位置各试两种括号，逐串扫前缀：O(n × 4ⁿ)", "只枚举左右各 n 个的位置，不用看前缀就全是答案", "只枚举 n 次独立的 ()，时间 O(n) 且能生成所有串"], answer=0,
                 why="每个合法串都在长度 2n 的二进制选择里。扫每条候选时用余额记左括号减右括号，曾经为负或最终不为零都不合法；这是直接但浪费的保底。"),
            dict(k="waste", q="哪两种前缀没有必要继续填后面的格子？",
                 options=["已经打开超过 n 次，或曾经右括号比左括号多", "左括号暂时比右括号多，或刚好用完左括号", "当前前缀长度为奇数，或已经出现了至少一个右括号"], answer=0,
                 why="某类括号放多了不能撤销；暂时少关几个却可以以后关。把只能失败的前缀在构造时就剪掉，不必生成很多个共享这段坏前缀的完整串。"),
            dict(k="tool", q="怎样把前缀检查放进生成过程？",
                 options=["用回溯维护当前路径、已用左右括号数，每格只尝试合法动作", "用贪心每次只选一个合法字符，总是优先左括号", "用集合替代前缀顺序，只保留两种字符是否出现"], answer=0,
                 why="当前位置的字符可能有两个都合法，想列全就要分两支试。计数足以判断能否继续，路径用于在达到长度时拼出完整字符串。"),
            dict(k="state", q="已用了 left 个左括号和 right 个右括号，何时能再放？",
                 options=["left < n 可放左；right < left 才可放右", "left <= n 可放左；right <= left 就可放右", "left < n 可放左；right < n 就可放右，不必比较 left"], answer=0,
                 why="要一直保持 0 <= right <= left <= n。右括号必须能关掉一个尚未匹配的左括号；有这个不变量，长度到 2n 时两种括号自然都恰好用了 n 个。"),
        ],
        brute="""class Solution:
    def generateParenthesis(self, n):
        result = []
        for chars in itertools.product('()', repeat=2 * n):
            balance = 0
            for char in chars:
                balance += 1 if char == '(' else -1
                if balance < 0:
                    break
            else:
                if balance == 0:
                    result.append(''.join(chars))
        return result
""",
        cloze=dict(
            code="""class Solution:
    def generateParenthesis(self, n):
        result, path = [], []

        def build(left, right):
            if len(path) == 2 * n:
                result.append(''.join(path))
                return
            if ⟦1⟧:
                path.append('(')
                build(left + 1, right)
                path.pop()
            if ⟦2⟧:
                path.append(')')
                build(left, right + 1)
                path.pop()

        build(0, 0)
        return result
""",
            blanks=[dict(a="left < n", hint="左括号的额度还没用完"),
                    dict(a="right < left", hint="还有至少一个打开但没关上的左括号")],
        ),
        say="要列出所有合法方案，用回溯逐格填括号。已用左括号不足 n 就能放左，已用右括号严格少于左才放右；每一步都保证前缀能补成合法串。走到 2n 就收集，回退时弹出选择。有 C 个合法串时，时间 O(nC)，不计输出的额外空间 O(n)。",
        trap="放右括号条件一定是 right < left，不是 right <= left。两者相等时没有没关上的左括号，放右括号立刻造成坏前缀。",
    ),
    "house-robber": dict(
        read="一排房子各有一些钱，任何两间相邻房不能同时选，求能拿到的最大总金额。",
        steps=[
            dict(k="ask", q="是要返回偷哪几间，还是能偷到多少钱？",
                 options=["只要满足限制的最大总金额", "返回一组被选房子的下标", "返回在不触发警报时有多少种选法"], answer=0,
                 why="题目要最值而非具体方案。有好几组房子同样值钱也不要紧，不必保存路径，只要保留已经考虑范围内的最高收益。"),
            dict(k="input", q="决定最后一间房拿不拿，会限制到哪些房？",
                 options=["拿了只会额外禁止它的前一间，更早的房子仍是同样的子问题", "最后一间拿了，前面所有房都禁止拿", "只要选了偶数下标，所有奇数房就全不能拿"], answer=0,
                 why="相邻限制只跨一格，是局部依赖。把最后一间的选择固定住，剩下的是更短一段前缀的同一问题，比逐个猜哪间钱多更有用。"),
            dict(k="brute", q="没想到状态复用时，如何把选择都算一遍？",
                 options=["递归取或不取最后一房，分别递归到前两间或前一间：最坏指数级", "每步挑金额最大的房，再把邻居排除：O(n log n)", "交替取奇数位和偶数位两套，选金额更高的一套：O(n)"], answer=0,
                 why="取当前间就跳过紧邻的一间，不取就只少当前一间，两支比较结果。朴素递归结点数满足 T(n) = T(n-1) + T(n-2) + O(1)，是指数级，不是只扫一遍。"),
            dict(k="waste", q="为什么两条看似不同的递归分支会做重复功？",
                 options=["直接少两间与连续两次少一间，最终都在求同一前缀最大收益", "两个房间只要钱一样，它们的相邻关系也就一样", "递归只有在房子金额全相等时才会遇到同一状态"], answer=0,
                 why="小问题由“还剩多少间前缀房子”确定，同一前缀不管怎样抵达，答案都相同。既然会反复求它，可以从短到长每个前缀只算一次。"),
            dict(k="tool", q="想用常数空间计算前缀答案，手里要留什么？",
                 options=["动态规划，只留上一个和上上个前缀最优值", "贪心，用一个变量记录到目前为止金额最大的房", "滑动窗口，只查看金额最大的两个相邻房间"], answer=0,
                 why="扩展一个前缀时只用到前两个长度的结果，早于它们的最值在当前决定里用不到。滚动保留两个值，空间就不随房屋数量增长。"),
            dict(k="state", q="设 dp[i] 是前 i 间房的最大金额，怎样求下一格？",
                 options=["取 max(dp[i-1], dp[i-2] + nums[i-1])", "取 max(dp[i-1] + nums[i-1], dp[i-2])", "取 max(dp[i-1], nums[i-1])，已经选择的房不能再合并"], answer=0,
                 why="不拿第 i 间保留 dp[i-1]；拿它不能直接加在相邻的前缀最值上，只能加到前 i-2 间的最值。空前缀收益为零，处理第一间时用两个零启动即可。"),
        ],
        brute="""class Solution:
    def rob(self, nums):
        def try_last(index):
            if index < 0:
                return 0
            skip = try_last(index - 1)
            take = nums[index] + try_last(index - 2)
            return max(skip, take)

        return try_last(len(nums) - 1)
""",
        cloze=dict(
            code="""class Solution:
    def rob(self, nums):
        older = previous = 0
        for money in nums:
            take = ⟦1⟧
            current = ⟦2⟧
            older, previous = previous, current
        return previous
""",
            blanks=[dict(a="older + money", hint="拿当前房时，收益只能接在前两格之前的前缀上"),
                    dict(a="max(previous, take)", hint="比较不拿当前房和拿当前房两种收益")],
        ),
        say="相邻不能同时选，我按前缀做动态规划，状态是前 i 间最多能拿的钱。不拿当前间就继承上一前缀；拿它就加在上上个前缀上，比较取大。每次只依赖前两格，用两个变量滚动更新，时间 O(n)，额外空间 O(1)。",
        trap="取当前房时加的是上上个前缀，而不是上一前缀。后者的最优选择可能已包含紧邻的上一间，例如 [2, 3] 就不能拿到 5。",
    ),
    "longest-increasing-subsequence": dict(
        read="从数组里按原下标顺序挑数，可以跳着挑，但选出的值必须严格递增，返回最多能挑几个。",
        steps=[
            dict(k="ask", q="[1, 4, 2, 3] 的答案该怎么交？",
                 options=["整数 3，例如可以挑 1、2、3", "数组 [1, 2, 3]，必须交出具体方案", "整数 2，因为只能找紧挨着的上升片段"], answer=0,
                 why="只输出长度，所以算法可只保留足够算长度的信息，不必重建一个具体子序列。“子序列”又允许跳过 4，并不要求下标相邻。"),
            dict(k="input", q="挑下一个数时，要保留原数组的什么？",
                 options=["保留下标顺序，且新数必须严格大于上一个挑的数", "可把原数组排序，只要最后挑出的值是按升序的", "保留值的非递减顺序，出现几个相同数就都能接上"], answer=0,
                 why="输入无需有序，也不能先排序，它表达的是候选到达的先后。严格递增则意味着相等值不能接上，这会决定二分时是找大于还是大于等于。"),
            dict(k="brute", q="用取或不取来枚举子序列，怎样做直接又不会改掉顺序？",
                 options=["按原下标递归取舍，取时检查是否比上次大：最坏 O(2ⁿ)", "把输入排序后去重，不同值的个数就是答案：O(n log n)", "只比较相邻两项，遇到下降就把长度清零：O(n)"], answer=0,
                 why="每个下标有取或不取的选择，取时检查单调性就能剪掉坏路径。已严格递增的输入不能靠这条规则剪枝，最多仍要遍历完整的二叉选择树。"),
            dict(k="waste", q="有两个同样长的合法前缀，结尾分别是 4 和 7，未来更值得留谁？",
                 options=["留结尾 4，它能接上的未来项覆盖结尾 7 的全部选项", "留结尾 7，越大才代表上升越充分", "两个都必须一直记完整路径，不然一定会漏答案"], answer=0,
                 why="只讨论已扫描的同一前缀：以后能接在 7 后的数也能接在 4 后，反过来不一定。对于每个长度，保留最易续接的结尾足够算长度，不必枚举完整路径。"),
            dict(k="tool", q="已经知道每种长度只需一个最小结尾，怎样快速找要更新的位置？",
                 options=["用升序数组 tails，二分找第一个不小于当前值的尾项", "用集合存尾项，集合长度加一就是下一轮长度", "只保留到目前最长的那条序列，接不上就把它丢掉"], answer=0,
                 why="取任一长度的最小尾值所对应的链，去掉最后一格，就得到更短且结尾更小的链。因此最小尾值随长度严格上升，可以二分定位当前值能接多长。"),
            dict(k="state", q="tails 每格代表什么，拿到二分位置 pos 后怎么做？",
                 options=["tails[pos] 是长度 pos + 1 的最小末尾；末尾位置则追加，否则替换", "tails 本身就是原数组中的最长序列；每轮必须追加当前值", "tails[pos] 是以下标 pos 结尾的最长长度；相等时延长"], answer=0,
                 why="pos 前的最小尾值都比当前值小，故能接在长度 pos 的链后；再长的链没有更小的末尾可接。用当前值改善长度 pos + 1 的结尾，不代表不同格来自同一真实子序列。"),
        ],
        brute="""class Solution:
    def lengthOfLIS(self, nums):
        def choose(index, last):
            if index == len(nums):
                return 0
            best = choose(index + 1, last)
            if last is None or nums[index] > last:
                best = max(best, 1 + choose(index + 1, nums[index]))
            return best

        return choose(0, None)
""",
        cloze=dict(
            code="""class Solution:
    def lengthOfLIS(self, nums):
        tails = []
        for value in nums:
            pos = ⟦1⟧
            if ⟦2⟧:
                tails.append(value)
            else:
                ⟦3⟧
        return len(tails)
""",
            blanks=[dict(a="bisect.bisect_left(tails, value)", hint="找首个不小于当前值的尾项，相等不允许延长"),
                    dict(a="pos == len(tails)", hint="尾项都比当前值小，才能增加最长长度"),
                    dict(a="tails[pos] = value", hint="只改善这个长度对应的最小末尾，不改长度")],
        ),
        say="子序列要保持原顺序，我边扫边对每种长度保留最小结尾，越小越好接后面的数。这些尾值严格升序；用二分找首个不小于当前值的位置，在那替换，若没有就追加并延长。尾值表的长度就是答案，时间 O(n log n)，额外空间 O(n)。",
        trap="严格递增用找首个大于等于的 bisect_left。若找成首个严格大于，像 [2, 2, 2] 会不断追加，错把等值算作增长。",
    ),
    "edit-distance": dict(
        read="一次可以插入、删除或替换一个字符，问把第一个单词变成第二个最少要做多少次。",
        steps=[
            dict(k="ask", q="把 cat 变成 cut 后，要返回什么？",
                 options=["整数 1，因为一次替换就够了", "字符串 cut，表示修改完成的结果", "具体操作列表，比如替换第二个字符"], answer=0,
                 why="返回的是最小代价，每种操作代价都是 1，不要求复原操作步骤。即使有多套最短操作，也只需要它们共同的次数。"),
            dict(k="input", q="比较两个前缀的末尾时，哪种情况可以不付代价？",
                 options=["末尾字符相同，可让它俩对齐，把问题缩成两个更短前缀", "只要前缀长度相同，末尾就可以免费对齐", "末尾不同也能直接丢掉两字符，之后再比较长度差"], answer=0,
                 why="操作只作用于单个字符，末尾对齐时只剩前缀需要转换。相同就免费配对；不同就要考虑对哪个前缀减一，这比真的在字符串上试插入、删除、替换更易表示。"),
            dict(k="brute", q="不先写递推表，最直接怎样试出最少编辑次数？",
                 options=["从末尾按操作次数逐层试删、插、替换；不去重时最坏指数级", "只替换不同的位置，再补删到目标长度，就一定最优", "把两个串分别排序，再用单指针数不同字符"], answer=0,
                 why="免费跳过相同末尾，再为三种编辑开分支。按次数从少到多枚举，首次把两侧耗空就是最优。不去重会指数爆炸；保底代码只入队不同长度对，最多 O((m+1)(n+1)) 个，每个分支仍可能花 O(min(m,n)+1) 再扫相同末尾。"),
            dict(k="waste", q="逐步试操作时，哪些问题可能被算多次？",
                 options=["不管先缩哪一个前缀，后来遇到同样的长度对 (i, j)，剩余问题相同", "出现相同的末尾字符时，两前缀一定有同样的编辑距离", "只要 i + j 相等，所有前缀对就能用一个结果"], answer=0,
                 why="先删后插与先插后删都可能落到 (i-1, j-1)。两个长度唯一确定了两个原串的前缀，操作的历史不影响它们之间的最少距离，因此只需算一次。"),
            dict(k="tool", q="填表时只用到上方、左方和左上方，怎样省空间？",
                 options=["前缀动态规划，用一行滚动数组并额外保存覆盖前的左上角", "只留当前行，不保存被覆盖的任何旧值", "用最长公共子序列长度唯一推出距离，不需要建编辑状态"], answer=0,
                 why="原二维表按行从左到右更新。写当前格时，原 dp[j] 是上方，新 dp[j-1] 是左方；左上方刚被覆盖，需在更新前另存一个变量供下一格。"),
            dict(k="state", q="D[i][j] 表示前 i 个转成前 j 个的最小次数，末尾不等怎么转移？",
                 options=["1 + min(上方删除、左方插入、左上方替换)", "1 + min(上方、左方)，因为替换等于先删再插", "1 + 左上方，末尾不同只能执行替换"], answer=0,
                 why="删除消耗原串一个字符，所以取 D[i-1][j]；插入消耗目标串一个字符，取 D[i][j-1]；替换同时消耗两侧，取 D[i-1][j-1]。相等时直接用左上方；有一侧为空时答案是另一侧长度。"),
        ],
        brute="""class Solution:
    def minDistance(self, word1, word2):
        def skip_matches(first, second):
            while first and second and word1[first - 1] == word2[second - 1]:
                first -= 1
                second -= 1
            return first, second

        start = skip_matches(len(word1), len(word2))
        queue = deque([(start, 0)])
        seen = {start}
        while queue:
            (first, second), steps = queue.popleft()
            if first == second == 0:
                return steps
            choices = []
            if first:
                choices.append((first - 1, second))
            if second:
                choices.append((first, second - 1))
            if first and second:
                choices.append((first - 1, second - 1))
            for first_left, second_left in choices:
                state = skip_matches(first_left, second_left)
                if state not in seen:
                    seen.add(state)
                    queue.append((state, steps + 1))
""",
        cloze=dict(
            code="""class Solution:
    def minDistance(self, word1, word2):
        if len(word1) < len(word2):
            word1, word2 = word2, word1
        dp = list(range(len(word2) + 1))
        for row, first in enumerate(word1, 1):
            diagonal = dp[0]
            dp[0] = row
            for col, second in enumerate(word2, 1):
                above = dp[col]
                if first == second:
                    dp[col] = ⟦1⟧
                else:
                    dp[col] = ⟦2⟧
                diagonal = ⟦3⟧
        return dp[-1]
""",
            blanks=[dict(a="diagonal", hint="字符相同，免费配对并同时缩短两侧前缀"),
                    dict(a="1 + min(above, dp[col - 1], diagonal)", hint="在删、插、替换三个来源中挑便宜的，再花一次操作"),
                    dict(a="above", hint="旧行正上方的值，在下一列会变成左上方")],
        ),
        say="算最少转换次数，我用两个前缀的最小编辑距离做状态。末尾相同就免费配对，否则比较删原串末尾、插目标串末尾、替换这三个子问题再加一。空前缀需要补足长度。滚动一行时额外留旧左上角，并用短串做列，时间 O(mn)（两串非空），额外空间 O(min(m,n)+1)。",
        trap="从左到右更新时，dp[col - 1] 已是当前行，不能拿它冒充左上角。覆盖 dp[col] 前先读旧值，更新完成后留给下一列。",
    ),
    "jump-game": dict(
        read="每格数字告诉你最多能往前跳几格，判断从数组第一个位置出发能不能到最后一个位置。",
        steps=[
            dict(k="ask", q="走得到最后一格后，题目还要求返回走法吗？",
                 options=["不要求，只返回能否到达", "要求返回跳跃次数最少的次数", "要求返回从开头到末尾的下标路线"], answer=0,
                 why="这是可达性，不是最少步数。即使同一个位置有很多条路可到，只要它可达，它能继续去的地方就和来路无关。"),
            dict(k="input", q="一格写着 3，能从它跳到哪些后续位置？",
                 options=["可以向前跳 1、2 或 3 格，只要落在数组内", "只能正好向前跳 3 格", "既可以向前跳，也可以向后跳，距离不超过 3"], answer=0,
                 why="“最远能跳”意味着不是固定步数，一个可达起点能覆盖右侧一整段。因此一路可达的下标不会出现洞，可以用一个右边界代表整段。"),
            dict(k="brute", q="按路线一条条试，怎样直接解决？",
                 options=["从 0 递归尝试所有合法落点，有一路到末尾就行，最坏指数级", "每次都必须跳当前允许的最远一步，遇零就失败", "逐格查看有没有零，有零就一定到不了末尾"], answer=0,
                 why="每次尝试从 1 到能力上限的每种步长，不漏路线，但不同的跳法可能落到同一个位置。若终点不可达，失败前可能枚举很多不同的跳跃组合。"),
            dict(k="waste", q="两条路线落到同一位置，还需要分别试后续吗？",
                 options=["不需要，能跳向哪只由当前格决定；还可以把所有可达位置压成一段", "需要，每条来路不同，后续最大跳距也不同", "不需要，因为所有走法的跳跃次数都相等"], answer=0,
                 why="不仅同一位置不必重搜，由于每一步允许所有较短距离，从一个可达位置推远右界时，中间的落点顺带也全被覆盖。只需保留最远边界就能表示到达情况。"),
            dict(k="tool", q="不存所有路线，怎样维护可达的最远位置？",
                 options=["贪心顺扫，用 far 记录所有已处理的可达起点能覆盖的最右端", "贪心只选一次最远跳，之后只处理那一个落点", "用最小堆先处理跳跃次数最少的路线，并保留所有路线"], answer=0,
                 why="这不是走一条总跳最远的路线，而是把每个已覆盖下标都当潜在起点。每个起点都只可能维持或延长最右边界，用一个变量就能累积这些信息。"),
            dict(k="state", q="扫描到 i，什么时候失败，什么时候延长 far？",
                 options=["i > far 就失败，否则用 max(far, i + nums[i]) 更新", "i >= far 就失败，否则直接令 far = i + nums[i]", "先用 i + nums[i] 延长 far，再判断 i 是否可达"], answer=0,
                 why="far 自己也可达；只有 i 大于它才说明出现第一个断点。不可达位置上的大跳距不能用来续命；可达位置只用它扩张右边界，不能把已知能到的范围缩小。"),
        ],
        brute="""class Solution:
    def canJump(self, nums):
        last = len(nums) - 1

        def try_from(index):
            if index == last:
                return True
            farthest = min(last, index + nums[index])
            for landing in range(index + 1, farthest + 1):
                if try_from(landing):
                    return True
            return False

        return try_from(0)
""",
        cloze=dict(
            code="""class Solution:
    def canJump(self, nums):
        far = 0
        for index, jump in enumerate(nums):
            if ⟦1⟧:
                return False
            far = ⟦2⟧
            if far >= len(nums) - 1:
                return True
        return True
""",
            blanks=[dict(a="index > far", hint="当前下标超出可达前缀，就不能使用它的跳距"),
                    dict(a="max(far, index + jump)", hint="新起点能把可达区间右端延长到哪里？")],
        ),
        say="题目只问是否到达，且每格给的是最大跳距，所以所有可达位置形成一个连续前缀。我从左往右扫，用 far 记右边界；当前下标超过它就失败，否则用当前位置加跳距扩张它。边界到末尾即可返回真，时间 O(n)，额外空间 O(1)。",
        trap="不要模拟每次跳到最远落点。[2, 2, 0, 0] 从 0 跳两格会卡住，但从 0 跳到 1 再跳到 3 就成功。",
    ),
    "network-delay-time": dict(
        read="信号从一个起点同时沿有向带权边传播，问等到最后一个节点收到需要多久，有点收不到就返回 -1。",
        steps=[
            dict(k="ask", q="已知每个点第一次收到信号的时间，怎样得出答案？",
                 options=["任一点不可达就给 -1，否则取所有首次到达时间的最大值", "把每个点的首次到达时间相加", "取起点出发的最大单条边权，不考虑多跳"], answer=0,
                 why="整张图的传播会并行发生，等全体收到只取决于谁是最后一个。每个节点的首达时间由最短路决定，不需要把多个节点的等待时间累计起来。"),
            dict(k="input", q="这里的最短路在比较什么，关键限制又是什么？",
                 options=["比较有向路径的边权和；边权均为正，少走一条边不一定更快", "只看经过边数；边上标出的时间不影响传播顺序", "比较边权和，但每条边都能倒着走"], answer=0,
                 why="信号只能沿箭头走，单条耗时大的边可能不如绕两条小权边。权重为正也意味着已走的时间不会被后续边抵消，可以利用这一点确定最近的节点。"),
            dict(k="brute", q="不懂最短路算法时，怎样直接从所有路线里选？",
                 options=["枚举从起点出发的不重复节点路径，为各终点取最小耗时：最坏可达阶乘级", "普通广搜，首次见到一个点就记最早时间：O(n + m)", "只比较每个节点最便宜的一条入边，把这些最小值加起来"], answer=0,
                 why="可以深搜试所有简单路径，带正权的回路只会花更多时间，最短路径不需要重复节点。节点很多且边密时，各种访问顺序都会变成候选，路径数会爆炸。"),
            dict(k="waste", q="同一节点有多条到达路线，哪部分不必反复向后算？",
                 options=["已经比最早到达更晚的前缀，沿后续相同路径也只会更晚", "所有先发现的路线都是浪费，只保留最后找到的那条", "边数多的路线总是浪费，无需比较它们的时间"], answer=0,
                 why="到达某节点之后可沿相同的出边继续走，所以更晚的到达不是更好的出发点。要省下后续枚举，先把当前最早能到的节点定下来，而不是先定最早被发现的节点。"),
            dict(k="tool", q="怎样每次先处理当前最早可到的节点？",
                 options=["Dijkstra，用邻接表和按到达时间排序的小根堆", "普通队列，优先处理最早发现的节点", "大根堆，优先处理到达时间最晚的节点"], answer=0,
                 why="堆顶是最小未处理到达时间。因为边权为正，任何绕经尚未定下的节点的路线，后半段都只会增加时间，所以堆顶的有效距离可以确定，再尝试更新它的出边。"),
            dict(k="state", q="堆里弹出 (d, u) 时，如何识别过期记录并更新邻居？",
                 options=["d 不等于 dist[u] 就跳过，否则只在 d + w 更小时改 dist[v] 并入堆", "u 第一次入堆就锁定，之后即使有更快的路也不更新", "每条出边都覆盖 dist[v]，不管新路线是否更短"], answer=0,
                 why="dist 是目前已知的最小到达时间；发现更快的路线时可以把新记录放入堆而不删除旧记录。弹出再核对，就不会拿过期值重新扫同一批边。"),
        ],
        brute="""class Solution:
    def networkDelayTime(self, times, n, k):
        graph = defaultdict(list)
        for source, dest, weight in times:
            graph[source].append((dest, weight))
        distance = [float('inf')] * (n + 1)
        path = {k}

        def visit(city, elapsed):
            distance[city] = min(distance[city], elapsed)
            for dest, weight in graph[city]:
                if dest not in path:
                    path.add(dest)
                    visit(dest, elapsed + weight)
                    path.remove(dest)

        visit(k, 0)
        last = max(distance[1:])
        return -1 if last == float('inf') else last
""",
        cloze=dict(
            code="""class Solution:
    def networkDelayTime(self, times, n, k):
        graph = defaultdict(list)
        for source, dest, weight in times:
            graph[source].append((dest, weight))
        distance = [float('inf')] * (n + 1)
        distance[k] = 0
        pending = [(0, k)]
        while pending:
            elapsed, city = heapq.heappop(pending)
            if elapsed != distance[city]:
                continue
            for dest, weight in graph[city]:
                arrival = ⟦1⟧
                if ⟦2⟧:
                    distance[dest] = arrival
                    ⟦3⟧
        last = max(distance[1:])
        return -1 if last == float('inf') else last
""",
            blanks=[dict(a="elapsed + weight", hint="沿这一条边走，要在已有耗时上再加多少？"),
                    dict(a="arrival < distance[dest]", hint="只有更快的到达路线才值得记录"),
                    dict(a="heapq.heappush(pending, (arrival, dest))", hint="把改进的候选入堆，按新到达时间排队")],
        ),
        say="全网等的是最迟首达点，所以先求起点到每个点的最短路。正权用 Dijkstra：邻接表存出边，小根堆按到达时间弹点，跳过过期记录，只把更短的邻居候选入堆。最后取距离最大值，有不可达就返回 -1。时间 O(n + m log(m+1))，空间 O(n+m)。",
        trap="不能在第一次入堆时锁定距离。例如起点到目标直达需 5，两条边绕过去只需 1 + 2，必须允许后来发现的路线改写旧值。",
    ),
    "accounts-merge": dict(
        read="把能通过共同邮箱直接或间接连起来的账户合并，每组先写用户名，再写排序去重后的邮箱。",
        steps=[
            dict(k="ask", q="合并成同一组后，返回的每组是什么形式？",
                 options=["第一项是用户名，其余是不重复且升序排列的邮箱", "只输出邮箱数量，不必列出地址", "把用户名和所有邮箱一起按字典序排序，不区分角色"], answer=0,
                 why="是构造新的账户记录，不是算合并次数。用户名位置固定；排序只作用于组内邮箱，多个组在总结果中按什么顺序列都可以。"),
            dict(k="input", q="哪些信息真正能把两个账户连接起来？",
                 options=["至少共享一个邮箱；通过别的账户间接连起来也应合并", "只要用户名相同，不管邮箱是否重合", "必须有完全相同的邮箱集合才算同一个人"], answer=0,
                 why="用户名可以重名，邮箱重合才是身份连接。若第一个账户和第二个共享邮箱、第二个和第三个共享另一个邮箱，就能把三者都归到同一组。"),
            dict(k="brute", q="不建邮箱索引，如何直接把相连的账户找齐？",
                 options=["逐对用邮箱集合检查交集，再搜连通块", "按用户名排序，直接把相同名字的相邻账户拼起来", "只比较输入中相邻账户，有交集才连接"], answer=0,
                 why="把每个账户视为图节点，共享邮箱时就连边，逐对检查不漏边。保底代码在搜索邻居时现查交集；A 个账户、E 个邮箱条目时，检查交集总时间至多 O(AE)，另加组内排序。"),
            dict(k="waste", q="同一个邮箱出现在很多账户里，要把这些账户两两连边吗？",
                 options=["不用，每个账户和第一个出现该邮箱的账户合并，整组就能连起来", "要，不然没连边的两账户不能归入同一组", "不用，取包含邮箱最多的账户保留，其余账户全部丢弃"], answer=0,
                 why="连通具有传递性。一个邮箱出现 k 次，留下一个代表，让后面的 k - 1 个账户接它就够了；无需为同一邮箱反复检查所有账户对。"),
            dict(k="tool", q="如何让每次邮箱重合都能迅速完成归组？",
                 options=["字典记邮箱首次出现的账户，用并查集合并账户编号", "字典以用户名为键，直接串接同名账户的邮箱", "用一个集合去掉全部重复邮箱，再把剩余邮箱当成一个组"], answer=0,
                 why="字典下标是邮箱，让我们直接定位一个已有连接，不必搜其他账户。并查集回答“两账户目前同组吗”并连接两组；早先的代表不必已经是当前的根。"),
            dict(k="state", q="所有邮箱处理完后，按什么键归集每个账户的邮箱？",
                 options=["并查集最终根编号；同根放一个集合，然后按字典序输出邮箱", "首次见到各邮箱时保存的账户编号，不再查根", "账户旧的直接父编号，不必沿父链找最终代表"], answer=0,
                 why="后面一次合并可能改变早期账户的代表，中间的父节点也可能不是根。确认连接全部建立后再对每个账户找最终根，才能把传递归并的邮箱放到同一个组。"),
        ],
        brute="""class Solution:
    def accountsMerge(self, accounts):
        emails = [set(account[1:]) for account in accounts]
        visited = set()
        result = []
        for start in range(len(accounts)):
            if start in visited:
                continue
            stack = [start]
            visited.add(start)
            group = set()
            while stack:
                current = stack.pop()
                group.update(emails[current])
                for other, addresses in enumerate(emails):
                    if other not in visited and not emails[current].isdisjoint(addresses):
                        visited.add(other)
                        stack.append(other)
            result.append([accounts[start][0]] + sorted(group))
        return result
""",
        cloze=dict(
            code="""class Solution:
    def accountsMerge(self, accounts):
        parent = list(range(len(accounts)))
        size = [1] * len(accounts)

        def find(index):
            while index != parent[index]:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def join(first, second):
            first, second = find(first), find(second)
            if first == second:
                return
            if size[first] < size[second]:
                first, second = second, first
            parent[second] = first
            size[first] += size[second]

        first_owner = {}
        for index, account in enumerate(accounts):
            for email in account[1:]:
                if email in first_owner:
                    ⟦1⟧
                else:
                    first_owner[email] = index

        groups = defaultdict(set)
        for index, account in enumerate(accounts):
            groups[⟦2⟧].update(account[1:])
        return [[accounts[root][0]] + sorted(emails) for root, emails in groups.items()]
""",
            blanks=[dict(a="join(index, first_owner[email])", hint="同一邮箱出现时，把新账户连到已记录的那个账户"),
                    dict(a="find(index)", hint="用全部合并完成之后的代表编号归组")],
        ),
        say="身份连接靠邮箱不是用户名，且连接可传递。我用字典存邮箱首次所属账户，重复遇到时就用并查集合并编号。处理完再按最终根收集去重邮箱并排序。A 个账户、E 个邮箱条目时，合并近线性，额外排序至多 O(E log E)，空间 O(A+E)。",
        trap="不要按名字归并，也不要边合并边用临时根整理最终输出。后来的共享邮箱可能把先前两个组连起来，应在所有合并结束后统一压根归组。",
    ),
    "coin-change-ii": dict(
        read="每种面额的硬币可以拿任意枚，求恰好凑出目标金额有多少种取法，只看各面额拿了几枚。",
        steps=[
            dict(k="ask", q="凑 3 时，先拿 1 再拿 2，和反过来拿，计几种？",
                 options=["一种，取用的硬币枚数完全相同", "两种，拿硬币的先后顺序不同", "一种，但只返回需要的硬币最少枚数"], answer=0,
                 why="题目问组合数：只要每种面额的数量一样，就不是新方案。既不是返回所有列表，也不是求最少几枚，最后要把互不重叠的取法数量加起来。"),
            dict(k="input", q="“每种硬币任意多次”意味着什么？",
                 options=["同一面额可多次使用，但总金额不能超过目标", "每种硬币至多出现一枚，因为只有一个面额值", "一次选定一种面额后，剩余金额不能再用别的面额"], answer=0,
                 why="这是可重复选择，不是每种选或不选的二叉选择。又因为无视先后，可以固定面额处理顺序：给每种面额确定枚数即可唯一描述一个组合。"),
            dict(k="brute", q="怎么直接枚举，既覆盖所有组合又不重复排列？",
                 options=["按面额递归枚举拿 0 枚到剩余金额能容纳的上限，分支数可能很大", "每一步枚举下一枚用哪个面额，所有走法都分别计数", "每个面额只试拿一枚或不拿，复杂度 O(2ⁿ)"], answer=0,
                 why="一层只决定一种硬币拿几枚，所有合法数量向量都能被枚举到。若金额是 A，m 种面额每层至多 A+1 个分支，递归粗略上界是 O((m+1) × (A+1)ᵐ)，远大于按金额填表。"),
            dict(k="waste", q="不同的前几种硬币取法，何时会问到同一个子问题？",
                 options=["处理到同一面额且剩余金额相同，后续的组合数相同", "只要剩余金额相同，即使可用的面额不一样也能用同一答案", "只要用了同样多的硬币，剩余组合数就必定相同"], answer=0,
                 why="比如拿一个 2 或拿两个 1，可能给后面的面额都留下金额 5。它们是不同的完整组合前缀，但可共用“用这些剩余面额凑 5 有几种”的计算。"),
            dict(k="tool", q="怎样在一张金额表中同时做到可以重复、不会重算排列？",
                 options=["完全背包计数：面额在外层，金额从小到大在内层", "金额在外层，再尝试最后放进去的每种面额", "面额在外层，金额从大到小扫，禁止用到本轮更新"], answer=0,
                 why="面额放外层让同一组枚数只按固定次序被计入。金额向上扫时，小金额的结果已经可以使用本轮硬币，拿来再加一枚，就实现了可重复使用。"),
            dict(k="state", q="dp[total] 表示用已处理面额凑到 total 的组合数，本轮怎么更新？",
                 options=["从 dp[0] = 1 开始，total >= coin 时加上 dp[total - coin]", "从 dp[0] = 0 开始，把所有可用的历史金额组合数累加", "total >= coin 就用 dp[total - coin] 覆盖旧值，不必相加"], answer=0,
                 why="旧 dp[total] 是不拿当前面额的方案。拿至少一枚的方案去掉一枚后，正好对应本轮已更新的 dp[total - coin]。两类互不重叠，凑零的一种方式是全都不拿。"),
        ],
        brute="""class Solution:
    def change(self, amount, coins):
        def count(index, left):
            if left == 0:
                return 1
            if index == len(coins):
                return 0
            coin = coins[index]
            ways = 0
            for copies in range(left // coin + 1):
                ways += count(index + 1, left - copies * coin)
            return ways

        return count(0, amount)
""",
        cloze=dict(
            code="""class Solution:
    def change(self, amount, coins):
        dp = [0] * (amount + 1)
        dp[0] = ⟦1⟧
        for coin in coins:
            for total in ⟦2⟧:
                dp[total] += ⟦3⟧
        return dp[amount]
""",
            blanks=[dict(a="1", hint="凑到零元时，什么都不选也算一个组合"),
                    dict(a="range(coin, amount + 1)", hint="从放得下一枚的最小金额开始，沿哪个方向能重复用？"),
                    dict(a="dp[total - coin]", hint="取走本轮的一枚硬币后，要凑的剩余金额是多少？")],
        ),
        say="这里是可重复选的组合计数，用完全背包。dp[金额] 是用已处理面额凑到该金额的方案数，零金额有一个空方案。面额在外层以免把排列重复计数，金额从小到大更新；当前总金额的旧方案加上拿一枚后剩余金额的方案。时间 O(面额数 × (金额+1))，空间 O(金额+1)。",
        trap="外层别先扫金额。用面额 1、2 凑 3 时，金额外层会把先加 1 再加 2 与先加 2 再加 1 算成两种，这里它们是同一个组合。",
    ),
    "longest-palindromic-subsequence": dict(
        read="可以从字符串里删任意字符，但不能调换留下来的顺序，求最多能留下多长的一段回文子序列。",
        steps=[
            dict(k="ask", q="在 bbbab 中能跳过 a 取得 bbbb，要返回什么？",
                 options=["整数 4，表示最长回文子序列的长度", "字符串 bbbb，必须返回实际留下的字符", "整数 3，只取相邻字符组成的回文"], answer=0,
                 why="答案是最大长度，不要求重建回文。有“可以删除任意字符”这句，留下的四个 b 就能连成合法序列，不能误读成原串连续片段。"),
            dict(k="input", q="判断一个区间中能留下的回文，为何先看两端字符？",
                 options=["回文的外层是一对相同字符，区间两端不同就不可能两个都保留", "只要两端相同，原区间就整个是回文", "区间两端不同，就必须把两端同时删掉"], answer=0,
                 why="两端匹配就能包在内部回文的外面；两端不匹配时，任何可行选法至多选一个，也可以一个都不选。于是可以把问题缩成去掉一个或两个端点的内部区间。"),
            dict(k="brute", q="不保存区间结果，怎样直接递归？",
                 options=["两端同就剥掉成对端点，两端不同分别试去左或去右：最坏 O(2ⁿ)", "两端不同就固定去左，直到扫完整串：O(n)", "枚举所有连续区间并判断原样是否回文：O(n³)"], answer=0,
                 why="端点不同时不知道舍哪边更好，只好都算再取最大。端点相同则存在一个用两端的最优解，可以直接拿中间最优包起来；没有记忆化时分支仍可指数增长。"),
            dict(k="waste", q="在分叉递归里，哪部分可以共用？",
                 options=["先删左后删右与先删右后删左，会遇见同一内部区间", "任何长度相等的区间，最优长度都一样", "只要左端一样，右端的不同不会改变区间结果"], answer=0,
                 why="递归到同一对下标，就只剩同一段原字符串可选，之前怎样丢外边不再重要。因此下标对就是状态，最多有 O(n²) 个不同区间。"),
            dict(k="tool", q="怎样先算所有更小的区间，再用它们解决长区间？",
                 options=["区间动态规划：左端从右往左，右端从左往右，用一行滚动", "从左向右做中心扩展，只比较左右紧邻位置", "先按字符排序聚拢相等字母，再找最长回文"], answer=0,
                 why="固定左端 i，所需的 i+1 行已算完，本行较小的右端也已更新。滚动时 dp[j] 是去左端，dp[j-1] 是去右端；单独带一个旧对角值表示两端都去掉。"),
            dict(k="state", q="D[i][j] 是 s[i..j] 内的最长回文子序列长度，如何转移？",
                 options=["端点同则 D[i+1][j-1] + 2，否则取去左、去右结果的较大值", "端点同则整个区间长度，否则 D[i+1][j-1]", "端点不同则把去左结果和去右结果相加"], answer=0,
                 why="两端不同时，所有方案至少丢一端；相同时，最优解至少长 2。若它只用一个端点，可以把它的配对字符换成另一端；若两端都没用，还能在外面包一对。空区间长 0，单字符长 1。"),
        ],
        brute="""class Solution:
    def longestPalindromeSubseq(self, s):
        def choose(left, right):
            if left > right:
                return 0
            if left == right:
                return 1
            if s[left] == s[right]:
                return 2 + choose(left + 1, right - 1)
            return max(choose(left + 1, right), choose(left, right - 1))

        return choose(0, len(s) - 1)
""",
        cloze=dict(
            code="""class Solution:
    def longestPalindromeSubseq(self, s):
        dp = [0] * len(s)
        for left in range(len(s) - 1, -1, -1):
            dp[left] = 1
            inner = 0
            for right in range(left + 1, len(s)):
                skip_left = dp[right]
                if s[left] == s[right]:
                    dp[right] = ⟦1⟧
                else:
                    dp[right] = ⟦2⟧
                inner = ⟦3⟧
        return dp[-1]
""",
            blanks=[dict(a="inner + 2", hint="相同的端点成一对，包在内部最优回文外面"),
                    dict(a="max(skip_left, dp[right - 1])", hint="分别试舍掉左端或者右端，保留更长结果"),
                    dict(a="skip_left", hint="更新前这一格的区间，正好是下一列的内部区间")],
        ),
        say="子序列允许删除，我用区间内最长回文子序列长度做状态。两端相同，在内部最优外包一对；两端不同，至少舍一端，比较去左和去右的结果。左端倒序、右端顺序，滚动一行时保存旧对角值。时间 O(n²)，额外空间 O(n)。",
        trap="这是子序列，不是子串。比如 bbbab 能删掉中间的 a 留下 bbbb，最长连续回文却没有四个 b；遇到端点不同要比较两种舍弃，而非停止。",
    ),
    "longest-palindromic-substring": dict(
        read="从原字符串里截出一段最长的连续回文，不能跳过字符；如果最长的有好几段，就返回起点最靠左的那段。",
        steps=[
            dict(k="ask", q="babad 里 bab 和 aba 都长 3，应该返回什么？",
                 options=["字符串 bab，因为它从下标 0 开始，比 aba 靠左", "字符串 aba，因为并列时选字典序更小的", "整数 3，只需要返回最长长度", "两段都返回，只要长度都等于最长长度就行"], answer=0,
                 why="先比长度、并列再比原串起点，不是比字典序，也不是任选其一。计算时记住最好的一对起点和长度，最后按它们切回原串；babad 的 bab 在下标 0、aba 在下标 1，故选 bab。"),
            dict(k="input", q="只能截取连续子串，回文又给了哪条可利用的限制？",
                 options=["在同一个中心两侧，距离相同的两个字符必须相等", "只要两端相等，内部就不用检查", "只要字符次数都是偶数或至多一个为奇数，原片段就是回文"], answer=0,
                 why="关键不是字符能不能重排，而是原位置的镜像配对。拿 abba 来看，中心落在两个 b 之间；b 与 b 相等还不够，外侧 a 与 a 也得相等。已经验证过的内部可以在扩大的同中心回文里复用。"),
            dict(k="brute", q="不利用对称性复用结果，最直接怎么写、要多慢？",
                 options=["枚举所有左、右端点，每段独立倒序判回文：最坏 O(n³)", "只枚举左端点，到第一个回文就停：最坏 O(n²)", "枚举所有删字符方式，选留下的最长回文：最坏 O(2ⁿ)"], answer=0,
                 why="每段连续子串都有唯一一对端点，枚举 O(n²) 对不会漏解。单段切片并和反转后的字符串比较最多要 O(n)；所有字符相同也不能省掉这些复制，保底写法最坏 O(n³)。从左往右试起点，并列不更新就保住最左。"),
            dict(k="waste", q="独立判断 c、bcb、abcba 是不是回文，哪里在做重复功？",
                 options=["三段共用同一中心，外扩时不必把已证实的内部再检查一遍", "长度不同的片段没有任何可以共用的信息", "这三个子串同中心，因此不用比较外层字符都是真回文"], answer=0,
                 why="bcb 一旦确认是回文，abcba 只需再检查新增的那对 a。如果新增的一对不相等，任何更大的同中心子串也会包含这对不等字符，可以立刻停，而不是另取更大区间从头判。"),
            dict(k="tool", q="长度为 n 的非空字符串，要尝试多少个中心，怎么扩展？",
                 options=["2n - 1 个：n 个字符中心、n - 1 个字符间隙，从中心双指针向外扩", "只试 n 个字符中心，偶数长回文也有一个正中字符", "只试 n - 1 个间隙中心，奇数长回文也可以从空窗口扩出来"], answer=0,
                 why="奇数长如 aba 从中间字符起步，偶数长如 cbbd 中的 bb 从相邻两格起步。二者都试才不漏解。也可以用区间 DP：dp[i][j] 表示 s[i..j] 是否整段回文，两端相等且内部回文才成立；Manacher 这里知道名字就够。"),
            dict(k="state", q="每次配对成功就令 L 左移、R 右移，首次失败后怎么取结果？",
                 options=["有效区间是 [L+1, R)，长度 R-L-1；等长时只留更小起点", "有效区间是 [L, R]，长度 R-L+1；等长时每次覆盖旧答案", "有效区间是 [L+1, R-1)，长度 R-L-2；等长时选字典序较小的"], answer=0,
                 why="停止时 L、R 指向没配成的两格，也可能已越界，所以只取它们之间。候选用起点 L+1 和长度更新，显式比较起点不依赖中心扫描顺序。等长片段的中心越靠左，起点也越靠左，所以从左到右试中心时，只在更长时更新也能保住最左。"),
        ],
        brute="""class Solution:
    def longestPalindrome(self, s):
        best = ""
        for start in range(len(s)):
            for end in range(start + 1, len(s) + 1):
                part = s[start:end]
                if part == part[::-1] and len(part) > len(best):
                    best = part
        return best
""",
        cloze=dict(
            code="""class Solution:
    def longestPalindrome(self, s):
        start, best = 0, 1
        for center in range(2 * len(s) - 1):
            left, right = ⟦1⟧
            while ⟦2⟧:
                left -= 1
                right += 1
            length = ⟦3⟧
            candidate = left + 1
            if length > best or (length == best and candidate < start):
                start, best = candidate, length
        return s[start:start + best]
""",
            blanks=[dict(a="center // 2, (center + 1) // 2", hint="编号 0 试 (0,0)，编号 1 试 (0,1)，编号 2 试 (1,1)，交替放中心"),
                    dict(a="left >= 0 and right < len(s) and s[left] == s[right]", hint="先保证左右都在串内，再检查这对镜像字符是否相等"),
                    dict(a="right - left - 1", hint="两指针停在成功范围的外侧，数它们之间的字符")],
        ),
        say="子串必须连续，回文则绕一个中心对称，所以枚举每个字符和每个相邻间隙，共 2n - 1 个中心。每次扩展只检查新添的两个字符，一旦不匹配或越界就停，此时有效区间是左指针下一格到右指针之前。同长度比较起点，保留最左。时间 O(n²)，除输出外空间 O(1)。",
        trap="别只从单个字符扩展，否则 cbbd 的 bb 会漏掉。扩展停下时两指针都不属于回文；另外 babad 的 bab 和 aba 等长，不能用“长度大于等于”直接覆盖旧答案。",
    ),
}
