LABS = [
    dict(
        id="lab-sql-metrics",
        course="dev",
        title="用 SQL 汇总评测运行指标",
        level="medium",
        packages=["sqlite3"],
        desc=r'''### 背景
AI 评测平台每天都会产出大量逐用例结果，工程师不能只看几条日志就判断模型是否变好，而要把一次运行的通过率、标签维度短板、延迟分位数和 token 成本汇总成稳定报表。面试里这类题常考察你是否能把 Python 与 SQL 分清边界：过滤、聚合、排序、分位点应尽量交给数据库完成，Python 负责组织返回结构和处理空结果。真实工作中，P95 延迟经常因为“向上取整第几个样本”、排序方向、空集合等细节写错，导致同一批数据在不同报表里对不上。
### 要实现什么
实现 `build_report(conn, run_id)`。`conn` 是已经建好表并插入数据的 `sqlite3.Connection`，表名为 `results`，字段包含 `case_id`、`tag`、`passed`、`latency_ms`、`tokens`、`run_id`。只统计指定 `run_id`。返回字典：`run_id`、`total`、`passed`、`pass_rate`、`p95_latency_ms`、`avg_tokens`、`by_tag`。总体 `pass_rate=passed/total`，空运行时为 `0.0`；`p95_latency_ms` 取按 `latency_ms` 升序排列后第 `ceil(0.95*n)` 个值，空运行为 `None`；`avg_tokens` 为空时为 `None`。`by_tag` 是列表，每项含 `tag,total,passed,pass_rate`，按 `pass_rate` 升序、再按 `tag` 升序排列。`passed` 字段按 0/1 处理。
### 例子
某次运行有 4 条结果，3 条通过，延迟为 `[10, 20, 30, 40]`，则总体通过率为 `0.75`，P95 是第 `ceil(3.8)=4` 个值 `40`。如果 `hard` 标签 1/2 通过、`easy` 标签 2/2 通过，`by_tag` 中 `hard` 排在前面。
### 约束
只能使用标准库和 `sqlite3`。核心统计必须通过 SQL 完成，尤其是分标签聚合和 P95 的排序取位。不要修改数据库内容，不要联网，不要依赖系统时间。浮点结果允许常规 Python 浮点误差，测试会用近似比较。''',
        starter=r'''def build_report(conn, run_id):
    """Build aggregate metrics for one evaluation run from a sqlite3 connection."""
    raise NotImplementedError
''',
        tests=r'''import sqlite3


def _metrics_conn(rows):
    conn = sqlite3.connect(":memory:")
    conn.execute("create table results(case_id text, tag text, passed integer, latency_ms real, tokens integer, run_id text)")
    conn.executemany("insert into results values(?,?,?,?,?,?)", rows)
    return conn


def test_builds_overall_metrics_and_p95():
    """验证总体通过率、平均 token 和 ceil 规则的 P95 延迟。"""
    conn = _metrics_conn([
        ("c1", "easy", 1, 10, 100, "r1"),
        ("c2", "easy", 1, 20, 120, "r1"),
        ("c3", "hard", 0, 30, 140, "r1"),
        ("c4", "hard", 1, 40, 160, "r1"),
        ("x", "easy", 0, 999, 999, "other"),
    ])
    got = build_report(conn, "r1")
    assert got["total"] == 4 and got["passed"] == 3, got
    assert abs(got["pass_rate"] - 0.75) < 1e-9, got
    assert got["p95_latency_ms"] == 40, got
    assert abs(got["avg_tokens"] - 130.0) < 1e-9, got


def test_groups_by_tag_sorted_by_worst_pass_rate():
    """验证标签报表按通过率升序排列，方便先看短板。"""
    conn = _metrics_conn([
        ("c1", "easy", 1, 10, 10, "r1"),
        ("c2", "easy", 1, 11, 10, "r1"),
        ("c3", "hard", 0, 12, 10, "r1"),
        ("c4", "hard", 1, 13, 10, "r1"),
        ("c5", "medium", 0, 14, 10, "r1"),
    ])
    by_tag = build_report(conn, "r1")["by_tag"]
    assert [x["tag"] for x in by_tag] == ["medium", "hard", "easy"], by_tag
    assert by_tag[0]["pass_rate"] == 0.0, by_tag
    assert by_tag[1]["total"] == 2 and by_tag[1]["passed"] == 1, by_tag


def test_empty_run_returns_stable_empty_report():
    """验证没有匹配运行时返回稳定结构而不是除零或抛错。"""
    conn = _metrics_conn([("c1", "easy", 1, 10, 10, "r1")])
    got = build_report(conn, "missing")
    assert got == {
        "run_id": "missing", "total": 0, "passed": 0, "pass_rate": 0.0,
        "p95_latency_ms": None, "avg_tokens": None, "by_tag": []
    }, got
''',
        hidden=r'''import sqlite3


def _metrics_conn_hidden(rows):
    conn = sqlite3.connect(":memory:")
    conn.execute("create table results(case_id text, tag text, passed integer, latency_ms real, tokens integer, run_id text)")
    conn.executemany("insert into results values(?,?,?,?,?,?)", rows)
    return conn


def test_p95_uses_ceiling_not_floor_or_interpolation():
    """验证 20 条样本时 P95 取第 19 个而不是最大值或插值。"""
    rows = [(f"c{i}", "t", 1, i, 10, "r") for i in range(1, 21)]
    got = build_report(_metrics_conn_hidden(rows), "r")
    assert got["p95_latency_ms"] == 19, got


def test_tag_tie_breaks_by_tag_name():
    """验证标签通过率相同时按标签名稳定排序。"""
    conn = _metrics_conn_hidden([
        ("c1", "b", 1, 1, 1, "r"), ("c2", "b", 0, 2, 1, "r"),
        ("c3", "a", 1, 3, 1, "r"), ("c4", "a", 0, 4, 1, "r"),
    ])
    got = build_report(conn, "r")["by_tag"]
    assert [x["tag"] for x in got] == ["a", "b"], got


def test_passed_values_are_summed_as_integers():
    """验证 passed 的 0/1 整数值被正确聚合。"""
    conn = _metrics_conn_hidden([("c1", "t", 0, 5, 7, "r"), ("c2", "t", 0, 6, 9, "r")])
    got = build_report(conn, "r")
    assert got["passed"] == 0 and got["pass_rate"] == 0.0, got
    assert got["avg_tokens"] == 8.0, got
''',
        solution=r'''def build_report(conn, run_id):
    """Build aggregate metrics for one evaluation run from a sqlite3 connection."""
    import math

    row = conn.execute(
        """
        select count(*) as total,
               coalesce(sum(case when passed then 1 else 0 end), 0) as passed,
               avg(tokens) as avg_tokens
        from results
        where run_id = ?
        """,
        (run_id,),
    ).fetchone()
    total = int(row[0])
    passed = int(row[1])
    avg_tokens = row[2]
    pass_rate = passed / total if total else 0.0

    p95_latency_ms = None
    if total:
        rank = math.ceil(0.95 * total)
        p95_row = conn.execute(
            """
            select latency_ms
            from (
                select latency_ms, row_number() over (order by latency_ms asc) as rn
                from results
                where run_id = ?
            )
            where rn = ?
            """,
            (run_id, rank),
        ).fetchone()
        p95_latency_ms = p95_row[0]

    by_tag = []
    for tag, tag_total, tag_passed in conn.execute(
        """
        select tag,
               count(*) as total,
               coalesce(sum(case when passed then 1 else 0 end), 0) as passed
        from results
        where run_id = ?
        group by tag
        order by (1.0 * coalesce(sum(case when passed then 1 else 0 end), 0) / count(*)) asc,
                 tag asc
        """,
        (run_id,),
    ):
        by_tag.append({
            "tag": tag,
            "total": int(tag_total),
            "passed": int(tag_passed),
            "pass_rate": tag_passed / tag_total if tag_total else 0.0,
        })

    return {
        "run_id": run_id,
        "total": total,
        "passed": passed,
        "pass_rate": pass_rate,
        "p95_latency_ms": p95_latency_ms,
        "avg_tokens": avg_tokens,
        "by_tag": by_tag,
    }
''',
        hints=["先用 where run_id=? 把一次运行过滤出来，再分别做总体和分标签聚合。", "P95 可以用 row_number() over(order by latency_ms) 后按 ceil(0.95*n) 取行。", "空运行要避免除零，并保持返回字段完整。"],
        points=["SQL 聚合与窗口排序", "评测指标口径一致性", "空集合与浮点比例处理"],
        numpy=False,
    ),
    dict(
        id="lab-sql-diff",
        course="dev",
        title="用 JOIN 对比两次评测运行",
        level="medium",
        packages=["sqlite3"],
        desc=r'''### 背景
模型、提示词或工具链升级后，测试开发工程师通常要回答四个问题：哪些用例从通过变成失败，哪些失败被修复，哪些是新纳入评测的数据，哪些旧用例不见了。只看新版本总体通过率很危险，因为新增简单用例可能掩盖核心场景回归；只看失败列表也会漏掉已经被删除的用例。面试官用这类题考察你是否熟悉 SQL 自连接、左连接、反连接，以及能否把数据差异组织成可给发布门禁使用的结构化结果。
### 要实现什么
实现 `diff_runs(conn, old_run_id, new_run_id)`。数据库中有 `results(case_id, tag, passed, latency_ms, tokens, run_id)` 表，每个运行内同一个 `case_id` 只出现一次。函数需要比较旧运行和新运行，返回字典：`old_run_id`、`new_run_id`、`regressions`、`fixes`、`added`、`deleted`、`summary`。`regressions` 是旧版 `passed=1` 且新版 `passed=0` 的用例列表；`fixes` 是旧版失败新版通过；`added` 是只在新版存在的用例；`deleted` 是只在旧版存在的用例。每个列表元素至少包含 `case_id` 和相关状态字段，列表按 `case_id` 升序。`summary` 记录四类数量。
### 例子
旧运行中 `a` 通过、`b` 失败、`c` 存在；新运行中 `a` 失败、`b` 通过、`d` 新增，则 `a` 是 regression，`b` 是 fix，`c` 是 deleted，`d` 是 added。
### 约束
只能使用标准库和 `sqlite3`。差异识别应主要通过 SQL JOIN/LEFT JOIN 完成，不要把整张表无脑读出后做嵌套循环。不要修改数据库内容；没有差异时返回空列表和 0 计数。''',
        starter=r'''def diff_runs(conn, old_run_id, new_run_id):
    """Compare two sqlite evaluation runs and return structured case differences."""
    raise NotImplementedError
''',
        tests=r'''import sqlite3


def _diff_conn(rows):
    conn = sqlite3.connect(":memory:")
    conn.execute("create table results(case_id text, tag text, passed integer, latency_ms real, tokens integer, run_id text)")
    conn.executemany("insert into results values(?,?,?,?,?,?)", rows)
    return conn


def test_detects_regressions_and_fixes():
    """验证旧过新不过、旧不过新过能被分到不同列表。"""
    conn = _diff_conn([
        ("a", "core", 1, 10, 100, "old"), ("b", "core", 0, 10, 100, "old"),
        ("a", "core", 0, 12, 110, "new"), ("b", "core", 1, 9, 90, "new"),
    ])
    got = diff_runs(conn, "old", "new")
    assert [x["case_id"] for x in got["regressions"]] == ["a"], got
    assert [x["case_id"] for x in got["fixes"]] == ["b"], got
    assert got["summary"]["regressions"] == 1 and got["summary"]["fixes"] == 1, got


def test_detects_added_and_deleted_cases():
    """验证只在新版或旧版存在的用例能被识别。"""
    conn = _diff_conn([
        ("old_only", "t", 1, 10, 10, "old"),
        ("same", "t", 1, 10, 10, "old"),
        ("same", "t", 1, 11, 10, "new"),
        ("new_only", "t", 0, 12, 10, "new"),
    ])
    got = diff_runs(conn, "old", "new")
    assert got["added"] == [{"case_id": "new_only", "tag": "t", "new_passed": 0}], got
    assert got["deleted"] == [{"case_id": "old_only", "tag": "t", "old_passed": 1}], got


def test_lists_are_sorted_by_case_id():
    """验证输出按 case_id 稳定排序，方便生成可读报告。"""
    conn = _diff_conn([
        ("z", "t", 1, 1, 1, "old"), ("a", "t", 1, 1, 1, "old"),
        ("z", "t", 0, 1, 1, "new"), ("a", "t", 0, 1, 1, "new"),
    ])
    got = diff_runs(conn, "old", "new")
    assert [x["case_id"] for x in got["regressions"]] == ["a", "z"], got
''',
        hidden=r'''import sqlite3


def _diff_conn_hidden(rows):
    conn = sqlite3.connect(":memory:")
    conn.execute("create table results(case_id text, tag text, passed integer, latency_ms real, tokens integer, run_id text)")
    conn.executemany("insert into results values(?,?,?,?,?,?)", rows)
    return conn


def test_unchanged_cases_do_not_appear_in_diff_lists():
    """验证两次状态相同的用例不会误报。"""
    conn = _diff_conn_hidden([
        ("p", "t", 1, 1, 1, "o"), ("f", "t", 0, 1, 1, "o"),
        ("p", "t", 1, 1, 1, "n"), ("f", "t", 0, 1, 1, "n"),
    ])
    got = diff_runs(conn, "o", "n")
    assert got["regressions"] == [] and got["fixes"] == [], got
    assert got["added"] == [] and got["deleted"] == [], got
    assert got["summary"] == {"regressions": 0, "fixes": 0, "added": 0, "deleted": 0}, got


def test_empty_old_run_marks_all_new_cases_added():
    """验证旧运行为空时，新运行全部算新增。"""
    conn = _diff_conn_hidden([("a", "x", 1, 1, 1, "new"), ("b", "y", 0, 1, 1, "new")])
    got = diff_runs(conn, "old", "new")
    assert [x["case_id"] for x in got["added"]] == ["a", "b"], got
    assert got["summary"]["added"] == 2, got


def test_output_contains_run_ids_for_traceability():
    """验证返回结构保留被比较的运行标识。"""
    got = diff_runs(_diff_conn_hidden([]), "r0", "r1")
    assert got["old_run_id"] == "r0" and got["new_run_id"] == "r1", got
''',
        solution=r'''def diff_runs(conn, old_run_id, new_run_id):
    """Compare two sqlite evaluation runs and return structured case differences."""
    regressions = [
        {"case_id": case_id, "tag": tag, "old_passed": int(old_passed), "new_passed": int(new_passed)}
        for case_id, tag, old_passed, new_passed in conn.execute(
            """
            select old.case_id, coalesce(new.tag, old.tag), old.passed, new.passed
            from results old
            join results new on old.case_id = new.case_id
            where old.run_id = ? and new.run_id = ? and old.passed = 1 and new.passed = 0
            order by old.case_id asc
            """,
            (old_run_id, new_run_id),
        )
    ]
    fixes = [
        {"case_id": case_id, "tag": tag, "old_passed": int(old_passed), "new_passed": int(new_passed)}
        for case_id, tag, old_passed, new_passed in conn.execute(
            """
            select old.case_id, coalesce(new.tag, old.tag), old.passed, new.passed
            from results old
            join results new on old.case_id = new.case_id
            where old.run_id = ? and new.run_id = ? and old.passed = 0 and new.passed = 1
            order by old.case_id asc
            """,
            (old_run_id, new_run_id),
        )
    ]
    added = [
        {"case_id": case_id, "tag": tag, "new_passed": int(new_passed)}
        for case_id, tag, new_passed in conn.execute(
            """
            select new.case_id, new.tag, new.passed
            from results new
            left join results old on old.case_id = new.case_id and old.run_id = ?
            where new.run_id = ? and old.case_id is null
            order by new.case_id asc
            """,
            (old_run_id, new_run_id),
        )
    ]
    deleted = [
        {"case_id": case_id, "tag": tag, "old_passed": int(old_passed)}
        for case_id, tag, old_passed in conn.execute(
            """
            select old.case_id, old.tag, old.passed
            from results old
            left join results new on new.case_id = old.case_id and new.run_id = ?
            where old.run_id = ? and new.case_id is null
            order by old.case_id asc
            """,
            (new_run_id, old_run_id),
        )
    ]
    return {
        "old_run_id": old_run_id,
        "new_run_id": new_run_id,
        "regressions": regressions,
        "fixes": fixes,
        "added": added,
        "deleted": deleted,
        "summary": {
            "regressions": len(regressions),
            "fixes": len(fixes),
            "added": len(added),
            "deleted": len(deleted),
        },
    }
''',
        hints=["共同存在的用例用 inner join，新增和删除用 left join + is null。", "回归和修复只看 passed 从 1 到 0 或从 0 到 1 的方向。", "所有列表都按 case_id 排序，避免测试和报告随机抖动。"],
        points=["SQL JOIN/反连接", "版本差异结构化表达", "发布回归门禁数据准备"],
        numpy=False,
    ),
    dict(
        id="lab-sql-badcase",
        course="agent",
        title="用窗口函数聚合失败 Badcase",
        level="hard",
        packages=["sqlite3"],
        desc=r'''### 背景
Agent 评测失败后，单条 badcase 往往只能说明一个现象，真正指导修复的是聚合视角：错误类型占比、某类错误集中在哪些工具、是否由少数工具贡献了大部分失败。真实团队会把这些结果用于选择下一轮修复优先级，例如先修解析错误、工具参数错误，还是知识检索问题。面试官会关注你是否会使用 SQL 窗口函数做 Top-N 分组，而不是在 Python 里写复杂而低效的多层循环。
### 要实现什么
实现 `summarize_badcases(conn)`。数据库中有 `failures(case_id, error_type, tool, message)` 表，每行是一条失败明细。返回字典：`total_failures` 和 `error_types`。`error_types` 是列表，每项包含 `error_type`、`count`、`share`、`top_tools`；`share=count/total_failures`，总数为 0 时列表为空。错误类型列表按 `count` 降序、再按 `error_type` 升序排序。`top_tools` 需要用窗口函数取该错误类型下出现次数最多的前 3 个工具，每项为 `{"tool": tool, "count": count}`，同次数按工具名升序。`tool` 为 NULL 时按字符串 `"<none>"` 聚合。
### 例子
如果 10 条失败里有 6 条是 `tool_error`，则该类 `share` 为 `0.6`。其中 `search` 出现 4 次、`calc` 出现 2 次，则 `top_tools` 为 `[search, calc]`。如果某类错误有 5 个工具并列或接近，只保留排序后的前 3 个。
### 约束
只能使用标准库和 `sqlite3`。Top 工具必须通过 SQL 窗口函数（如 `row_number() over(partition by ...)`）实现。不要修改数据库，不要联网。返回浮点占比即可，不要求格式化为百分号。''',
        starter=r'''def summarize_badcases(conn):
    """Summarize failed cases by error type and top tools from sqlite."""
    raise NotImplementedError
''',
        tests=r'''import sqlite3


def _badcase_conn(rows):
    conn = sqlite3.connect(":memory:")
    conn.execute("create table failures(case_id text, error_type text, tool text, message text)")
    conn.executemany("insert into failures values(?,?,?,?)", rows)
    return conn


def test_counts_share_and_error_type_order():
    """验证错误类型按数量降序聚合并计算占比。"""
    conn = _badcase_conn([
        ("c1", "tool_error", "search", "x"), ("c2", "tool_error", "search", "x"),
        ("c3", "tool_error", "calc", "x"), ("c4", "format_error", "parser", "x"),
    ])
    got = summarize_badcases(conn)
    assert got["total_failures"] == 4, got
    assert [x["error_type"] for x in got["error_types"]] == ["tool_error", "format_error"], got
    assert abs(got["error_types"][0]["share"] - 0.75) < 1e-9, got


def test_top_tools_uses_counts_and_limits_to_three():
    """验证每类错误只保留出现最多的前三个工具。"""
    rows = []
    rows += [(f"s{i}", "tool_error", "search", "") for i in range(4)]
    rows += [(f"c{i}", "tool_error", "calc", "") for i in range(3)]
    rows += [(f"b{i}", "tool_error", "browser", "") for i in range(2)]
    rows += [("o1", "tool_error", "other", "")]
    top = summarize_badcases(_badcase_conn(rows))["error_types"][0]["top_tools"]
    assert top == [
        {"tool": "search", "count": 4},
        {"tool": "calc", "count": 3},
        {"tool": "browser", "count": 2},
    ], top


def test_empty_failure_table_returns_empty_summary():
    """验证没有失败时返回空聚合。"""
    got = summarize_badcases(_badcase_conn([]))
    assert got == {"total_failures": 0, "error_types": []}, got
''',
        hidden=r'''import sqlite3


def _badcase_conn_hidden(rows):
    conn = sqlite3.connect(":memory:")
    conn.execute("create table failures(case_id text, error_type text, tool text, message text)")
    conn.executemany("insert into failures values(?,?,?,?)", rows)
    return conn


def test_tool_ties_are_sorted_by_tool_name():
    """验证工具次数并列时按名称升序稳定排序。"""
    conn = _badcase_conn_hidden([
        ("1", "e", "b", ""), ("2", "e", "a", ""), ("3", "e", "c", ""), ("4", "e", "d", ""),
    ])
    top = summarize_badcases(conn)["error_types"][0]["top_tools"]
    assert [x["tool"] for x in top] == ["a", "b", "c"], top


def test_null_tool_is_grouped_as_none_string():
    """验证 NULL 工具名不会丢失，而是归入 <none>。"""
    conn = _badcase_conn_hidden([("1", "e", None, ""), ("2", "e", None, ""), ("3", "e", "x", "")])
    top = summarize_badcases(conn)["error_types"][0]["top_tools"]
    assert top[0] == {"tool": "<none>", "count": 2}, top


def test_error_type_tie_breaks_by_name():
    """验证错误类型数量并列时按名称排序。"""
    conn = _badcase_conn_hidden([("1", "b", "t", ""), ("2", "a", "t", "")])
    got = summarize_badcases(conn)["error_types"]
    assert [x["error_type"] for x in got] == ["a", "b"], got
''',
        solution=r'''def summarize_badcases(conn):
    """Summarize failed cases by error type and top tools from sqlite."""
    total = conn.execute("select count(*) from failures").fetchone()[0]
    if total == 0:
        return {"total_failures": 0, "error_types": []}

    top_by_type = {}
    for error_type, tool, count in conn.execute(
        """
        with tool_counts as (
            select error_type, coalesce(tool, '<none>') as tool, count(*) as cnt
            from failures
            group by error_type, coalesce(tool, '<none>')
        ), ranked as (
            select error_type, tool, cnt,
                   row_number() over (partition by error_type order by cnt desc, tool asc) as rn
            from tool_counts
        )
        select error_type, tool, cnt
        from ranked
        where rn <= 3
        order by error_type asc, rn asc
        """
    ):
        top_by_type.setdefault(error_type, []).append({"tool": tool, "count": int(count)})

    error_types = []
    for error_type, count in conn.execute(
        """
        select error_type, count(*) as cnt
        from failures
        group by error_type
        order by cnt desc, error_type asc
        """
    ):
        error_types.append({
            "error_type": error_type,
            "count": int(count),
            "share": count / total,
            "top_tools": top_by_type.get(error_type, []),
        })
    return {"total_failures": int(total), "error_types": error_types}
''',
        hints=["先按 error_type/tool 聚合次数，再在每个 error_type 内排名。", "窗口函数 row_number() 的 partition by 是本题关键。", "NULL 工具名要先 coalesce，否则分组和返回结构容易不稳定。"],
        points=["SQL 窗口函数 Top-N", "Badcase 根因聚合", "占比和排序口径"],
        numpy=False,
    ),
    dict(
        id="lab-yaml-plan",
        course="dev",
        title="校验 YAML 评测配置并展开运行计划",
        level="medium",
        packages=["pyyaml"],
        desc=r'''### 背景
批量评测通常不是手写循环，而是由 YAML 配置驱动：数据集路径、模型列表、提示词版本、重复次数、并发和门禁阈值都来自配置文件。配置一旦写错，轻则浪费算力，重则让发布门禁形同虚设。面试官会用这类题考察你是否能做清晰的配置校验：不仅要发现错误，还要告诉调用方字段路径，例如 `models[0].name` 或 `gates.pass_rate`，这样使用者才能快速修复。
### 要实现什么
实现 `build_eval_plan(yaml_text)`。输入是 YAML 字符串，解析后校验并返回 `{"ok": True, "plan": [...], "gates": {...}}`；如果有错误，返回 `{"ok": False, "errors": [...]}`，每个错误包含 `path` 和 `message`。必填字段：`dataset.path` 非空字符串；`models` 非空列表，每个元素有非空 `name`；`prompts` 非空列表，每个元素有非空 `version`；`repeat` 为 1 到 20 的整数；`concurrency` 为 1 到 100 的整数；`gates.pass_rate` 为 0 到 1 的数字。运行计划是模型 × 提示词 × 重复的笛卡尔积，每项包含 `run_id`、`dataset_path`、`model`、`prompt_version`、`repeat_index`、`concurrency`。`repeat_index` 从 0 开始，`run_id` 要稳定可读。
### 例子
一个配置包含 2 个模型、3 个提示词、重复 2 次，应展开出 12 条计划。若 `gates.pass_rate: 1.2`，则返回错误路径 `gates.pass_rate`。
### 约束
只能使用标准库和 `pyyaml`。不要读取真实文件，不要联网。需要一次性收集尽可能多的错误，而不是遇到第一个错误就抛异常。YAML 语法错误也要转成 `ok=False` 的结构化错误。''',
        starter=r'''def build_eval_plan(yaml_text):
    """Validate a YAML evaluation config and expand it into deterministic run plans."""
    raise NotImplementedError
''',
        tests=r'''def test_expands_models_prompts_and_repeats():
    """验证模型、提示词和重复次数会展开成笛卡尔积计划。"""
    text = """
dataset:
  path: data/eval.jsonl
models:
  - name: small
  - name: large
prompts:
  - version: v1
  - version: v2
repeat: 2
concurrency: 4
gates:
  pass_rate: 0.85
"""
    got = build_eval_plan(text)
    assert got["ok"] is True, got
    assert len(got["plan"]) == 8, got
    assert got["plan"][0] == {
        "run_id": "small__v1__r0", "dataset_path": "data/eval.jsonl", "model": "small",
        "prompt_version": "v1", "repeat_index": 0, "concurrency": 4
    }, got["plan"][0]
    assert got["gates"] == {"pass_rate": 0.85}, got


def test_reports_multiple_field_path_errors():
    """验证配置错误会带字段路径并尽量一次性报出多个问题。"""
    text = """
dataset:
  path: ""
models: []
prompts:
  - version: ""
repeat: 0
concurrency: 101
gates:
  pass_rate: 1.2
"""
    got = build_eval_plan(text)
    assert got["ok"] is False, got
    paths = {e["path"] for e in got["errors"]}
    for path in ["dataset.path", "models", "prompts[0].version", "repeat", "concurrency", "gates.pass_rate"]:
        assert path in paths, (path, got)


def test_yaml_syntax_error_is_structured_error():
    """验证 YAML 语法错误不会直接抛出给调用方。"""
    got = build_eval_plan("dataset: [unterminated")
    assert got["ok"] is False, got
    assert got["errors"][0]["path"] == "$", got
''',
        hidden=r'''def test_missing_nested_sections_are_reported():
    """验证缺少顶层或嵌套字段时能给出准确路径。"""
    got = build_eval_plan("models:\n  - name: m\nprompts:\n  - version: v\nrepeat: 1\nconcurrency: 1\ngates: {}")
    paths = {e["path"] for e in got["errors"]}
    assert "dataset.path" in paths and "gates.pass_rate" in paths, got


def test_model_item_must_be_mapping_with_name():
    """验证模型列表元素格式错误时路径定位到具体下标。"""
    text = """
dataset: {path: data.jsonl}
models:
  - name: ok
  - bad
prompts:
  - version: v1
repeat: 1
concurrency: 1
gates: {pass_rate: 0.5}
"""
    got = build_eval_plan(text)
    assert got["ok"] is False, got
    assert any(e["path"] == "models[1].name" for e in got["errors"]), got


def test_repeat_and_concurrency_bool_are_not_accepted_as_ints():
    """验证 bool 不会被误当作整数范围值。"""
    text = """
dataset: {path: data.jsonl}
models: [{name: m}]
prompts: [{version: v}]
repeat: true
concurrency: false
gates: {pass_rate: 0.5}
"""
    got = build_eval_plan(text)
    paths = {e["path"] for e in got["errors"]}
    assert "repeat" in paths and "concurrency" in paths, got
''',
        solution=r'''def build_eval_plan(yaml_text):
    """Validate a YAML evaluation config and expand it into deterministic run plans."""
    import yaml

    try:
        cfg = yaml.safe_load(yaml_text)
    except Exception as exc:
        return {"ok": False, "errors": [{"path": "$", "message": f"YAML 解析失败: {exc}"}]}

    errors = []
    if not isinstance(cfg, dict):
        return {"ok": False, "errors": [{"path": "$", "message": "配置根节点必须是对象"}]}

    def add(path, message):
        errors.append({"path": path, "message": message})

    dataset = cfg.get("dataset")
    dataset_path = dataset.get("path") if isinstance(dataset, dict) else None
    if not isinstance(dataset_path, str) or not dataset_path.strip():
        add("dataset.path", "必须是非空字符串")

    models = cfg.get("models")
    valid_models = []
    if not isinstance(models, list) or not models:
        add("models", "必须是非空列表")
    else:
        for i, item in enumerate(models):
            name = item.get("name") if isinstance(item, dict) else None
            if not isinstance(name, str) or not name.strip():
                add(f"models[{i}].name", "必须是非空字符串")
            else:
                valid_models.append(name.strip())

    prompts = cfg.get("prompts")
    valid_prompts = []
    if not isinstance(prompts, list) or not prompts:
        add("prompts", "必须是非空列表")
    else:
        for i, item in enumerate(prompts):
            version = item.get("version") if isinstance(item, dict) else None
            if not isinstance(version, str) or not version.strip():
                add(f"prompts[{i}].version", "必须是非空字符串")
            else:
                valid_prompts.append(version.strip())

    repeat = cfg.get("repeat")
    if isinstance(repeat, bool) or not isinstance(repeat, int) or not (1 <= repeat <= 20):
        add("repeat", "必须是 1 到 20 的整数")

    concurrency = cfg.get("concurrency")
    if isinstance(concurrency, bool) or not isinstance(concurrency, int) or not (1 <= concurrency <= 100):
        add("concurrency", "必须是 1 到 100 的整数")

    gates = cfg.get("gates")
    pass_rate = gates.get("pass_rate") if isinstance(gates, dict) else None
    if isinstance(pass_rate, bool) or not isinstance(pass_rate, (int, float)) or not (0 <= pass_rate <= 1):
        add("gates.pass_rate", "必须是 0 到 1 的数字")

    if errors:
        return {"ok": False, "errors": errors}

    plan = []
    for model in valid_models:
        for prompt in valid_prompts:
            for repeat_index in range(repeat):
                plan.append({
                    "run_id": f"{model}__{prompt}__r{repeat_index}",
                    "dataset_path": dataset_path.strip(),
                    "model": model,
                    "prompt_version": prompt,
                    "repeat_index": repeat_index,
                    "concurrency": concurrency,
                })
    return {"ok": True, "plan": plan, "gates": {"pass_rate": float(pass_rate)}}
''',
        hints=["先 safe_load，再把所有字段校验错误收集到 errors 列表。", "列表里的错误路径要带下标，例如 models[1].name。", "Python 里 bool 是 int 的子类，校验整数范围时要显式排除 bool。"],
        points=["YAML 配置解析", "字段路径化错误报告", "配置驱动批量评测计划展开"],
        numpy=False,
    ),
    dict(
        id="lab-jsonl-clean",
        course="dev",
        title="清洗 JSONL 评测集并分层抽样",
        level="medium",
        packages=[],
        desc=r'''### 背景
评测集经常来自人工标注、线上日志或多轮数据合并，原始 JSONL 里可能混有坏行、重复输入、缺字段和标签分布不均。AI 评测工程师需要在真正跑模型前完成清洗：坏行要保留行号方便回溯，重复样本要按稳定规则去重，抽样要按标签分层避免小众场景被完全抽掉。面试官通常会考察你是否能写出确定性的清洗逻辑，并通过注入随机数对象让测试可复现。
### 要实现什么
实现 `clean_jsonl(text, sample_per_tag=None, rng=None)`。输入 `text` 是 JSONL 字符串，每行应是对象，至少包含非空字符串 `input` 和非空字符串 `tag`，可带任意其他字段。解析失败、不是对象、缺少必填字段的行要加入 `errors`，错误项包含 `line` 和 `error`。有效样本按规范化后的输入去重：对 `input` 做 `strip()`，再把连续空白折叠为一个空格并转小写作为去重键；同一键保留第一次出现的有效样本。返回 `{"items": [...], "errors": [...], "stats": {...}}`。输出样本中的 `input` 用去首尾空白但保留原大小写的文本，`tag` 保留原值。`stats` 至少包含 `lines`、`valid`、`kept`、`duplicates`、`errors`、`by_tag`。如果 `sample_per_tag` 是正整数，则每个标签最多保留这么多条，使用注入的 `rng.sample(seq, k)` 抽样，抽样后仍按原始行号升序输出。
### 例子
两行输入分别是 `" Hello   world "` 和 `"hello world"`，它们规范化键相同，只保留第一条，重复数加 1。若 `sample_per_tag=2`，某标签有 5 条，则用 `rng.sample` 选 2 条。
### 约束
只能使用标准库。不要读取文件、不要联网、不要在函数内部创建不可控随机行为覆盖传入的 `rng`；当需要抽样且 `rng` 为 `None` 时，可以使用标准库 `random` 模块。空行忽略但计入总行数，不算解析错误。''',
        starter=r'''def clean_jsonl(text, sample_per_tag=None, rng=None):
    """Parse, validate, deduplicate, optionally stratified-sample a JSONL dataset."""
    raise NotImplementedError
''',
        tests=r'''def test_parses_valid_lines_and_collects_bad_json_with_line_number():
    """验证合法行被保留，JSON 解析失败会记录行号。"""
    text = '{"input":"A","tag":"math"}\nnot json\n{"input":"B","tag":"code"}'
    got = clean_jsonl(text)
    assert [x["input"] for x in got["items"]] == ["A", "B"], got
    assert got["errors"][0]["line"] == 2, got
    assert got["stats"]["errors"] == 1, got


def test_deduplicates_by_normalized_input():
    """验证输入会按去首尾、折叠空白、小写后的键去重。"""
    text = '\n'.join([
        '{"input":" Hello   World ","tag":"t","id":1}',
        '{"input":"hello world","tag":"t","id":2}',
    ])
    got = clean_jsonl(text)
    assert len(got["items"]) == 1, got
    assert got["items"][0]["input"] == "Hello   World", got
    assert got["stats"]["duplicates"] == 1, got


def test_stratified_sampling_uses_injected_rng_and_preserves_line_order():
    """验证分层抽样使用注入 rng，并按原始行号输出。"""
    class LastTwoRng:
        def sample(self, seq, k):
            return list(seq)[-k:]
    text = '\n'.join([
        '{"input":"a1","tag":"a"}', '{"input":"a2","tag":"a"}', '{"input":"a3","tag":"a"}',
        '{"input":"b1","tag":"b"}', '{"input":"b2","tag":"b"}', '{"input":"b3","tag":"b"}',
    ])
    got = clean_jsonl(text, sample_per_tag=2, rng=LastTwoRng())
    assert [x["input"] for x in got["items"]] == ["a2", "a3", "b2", "b3"], got
    assert got["stats"]["by_tag"] == {"a": 2, "b": 2}, got
''',
        hidden=r'''def test_invalid_object_and_required_fields_are_errors():
    """验证非对象、空 input、空 tag 都会进入错误列表。"""
    text = '[1,2]\n{"input":" ","tag":"x"}\n{"input":"ok","tag":""}'
    got = clean_jsonl(text)
    assert got["items"] == [], got
    assert [e["line"] for e in got["errors"]] == [1, 2, 3], got


def test_empty_lines_are_counted_but_not_errors():
    """验证空行计入总行数，但不算坏行。"""
    got = clean_jsonl('\n{"input":"x","tag":"t"}\n  ')
    assert got["stats"]["lines"] == 3, got
    assert got["stats"]["errors"] == 0 and got["stats"]["kept"] == 1, got


def test_sample_per_tag_none_or_large_keeps_all_items():
    """验证不抽样或抽样上限大于标签数量时保留全部。"""
    text = '{"input":"x","tag":"t"}\n{"input":"y","tag":"t"}'
    assert len(clean_jsonl(text, sample_per_tag=None)["items"]) == 2
    assert len(clean_jsonl(text, sample_per_tag=5)["items"]) == 2
''',
        solution=r'''def clean_jsonl(text, sample_per_tag=None, rng=None):
    """Parse, validate, deduplicate, optionally stratified-sample a JSONL dataset."""
    import json
    import random
    import re

    def norm_input(value):
        return re.sub(r"\s+", " ", value.strip()).lower()

    errors = []
    items = []
    seen = set()
    valid = 0
    duplicates = 0
    lines = text.splitlines()

    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception as exc:
            errors.append({"line": line_no, "error": f"JSON 解析失败: {exc}"})
            continue
        if not isinstance(obj, dict):
            errors.append({"line": line_no, "error": "每行必须是 JSON 对象"})
            continue
        raw_input = obj.get("input")
        tag = obj.get("tag")
        if not isinstance(raw_input, str) or not raw_input.strip():
            errors.append({"line": line_no, "error": "input 必须是非空字符串"})
            continue
        if not isinstance(tag, str) or not tag.strip():
            errors.append({"line": line_no, "error": "tag 必须是非空字符串"})
            continue
        valid += 1
        key = norm_input(raw_input)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        item = dict(obj)
        item["input"] = raw_input.strip()
        item["tag"] = tag
        item["_line"] = line_no
        items.append(item)

    selected = items
    if sample_per_tag is not None:
        if isinstance(sample_per_tag, bool) or not isinstance(sample_per_tag, int) or sample_per_tag <= 0:
            raise ValueError("sample_per_tag 必须是正整数或 None")
        sampler = rng if rng is not None else random
        groups = {}
        for item in items:
            groups.setdefault(item["tag"], []).append(item)
        selected = []
        for tag in sorted(groups):
            group = groups[tag]
            if len(group) > sample_per_tag:
                selected.extend(sampler.sample(group, sample_per_tag))
            else:
                selected.extend(group)
        selected.sort(key=lambda item: item["_line"])

    clean_items = []
    by_tag = {}
    for item in selected:
        out = {k: v for k, v in item.items() if k != "_line"}
        clean_items.append(out)
        by_tag[out["tag"]] = by_tag.get(out["tag"], 0) + 1

    return {
        "items": clean_items,
        "errors": errors,
        "stats": {
            "lines": len(lines),
            "valid": valid,
            "kept": len(clean_items),
            "duplicates": duplicates,
            "errors": len(errors),
            "by_tag": by_tag,
        },
    }
''',
        hints=["逐行解析时保留 line_no，错误不要中断后续行处理。", "去重键和输出 input 不是同一个值：键要小写折叠空白，输出只 strip。", "分层抽样先按 tag 分组，用 rng.sample 后再按原始行号排序。"],
        points=["JSONL 数据清洗", "确定性去重与分层抽样", "数据质量统计与错误留痕"],
        numpy=False,
    ),
    dict(
        id="lab-stats-compare",
        course="agent",
        title="比较两个版本通过率的置信区间",
        level="hard",
        packages=[],
        desc=r'''### 背景
评测通过率从 80% 变成 84% 是否真的说明新版本更好？如果样本只有几十条，这个差异可能只是抽样波动；如果样本上千条，1% 的变化也可能值得关注。AI 评测工程师需要用统计方法给出更稳健的判断：单版本通过率的 Wilson 置信区间、两个版本差值的 bootstrap 区间、显著性判断，以及为了检测目标差异还需要多少样本。面试官会借这题考察你是否能把评测指标和不确定性一起报告，而不是只输出一个百分比。
### 要实现什么
实现 `compare_rates(old_results, new_results, rng, bootstrap_iters=1000, alpha=0.05, min_detectable_delta=0.05)`。`old_results` 和 `new_results` 是由 0/1 或 bool 组成的序列，表示逐样本是否通过；两组长度可以不同但都不能为空。返回字典包含：`old`、`new`、`diff`、`bootstrap_ci`、`significant`、`required_n_per_group`。`old/new` 各自包含 `n`、`passed`、`rate`、`wilson_ci`。`diff = new_rate - old_rate`。Wilson 区间使用常见正态近似，默认 95% 时可用 `z=1.96`；当 `alpha` 不是 0.05 时可使用标准库正态分布函数计算 z。bootstrap 对两组分别有放回重采样，重复 `bootstrap_iters` 次，记录差值分布并取双侧分位数。随机性必须来自注入的 `rng`，它至少提供 `randrange(n)`。
### 例子
旧版 `[1,1,0,0]` 通过率 0.5，新版 `[1,1,1,0]` 通过率 0.75，`diff` 为 0.25。若 bootstrap 差值区间不跨 0，则 `significant=True`，否则为 `False`。
### 约束
只能使用标准库。不要使用真实时间、全局随机数或第三方库。样本量估算使用两比例检验的粗略正态近似即可：每组样本数约为 `2 * p_pool * (1-p_pool) * (z_alpha/2 + z_power)^2 / delta^2`，默认 power 取 80% 的 `z_power=0.84`，向上取整。输入为空、结果不是 0/1/bool、迭代次数非正数都应抛出 `ValueError`。''',
        starter=r'''def compare_rates(old_results, new_results, rng, bootstrap_iters=1000, alpha=0.05, min_detectable_delta=0.05):
    """Compare two pass-rate samples with Wilson and bootstrap confidence intervals."""
    raise NotImplementedError
''',
        tests=r'''class CycleRng:
    def __init__(self):
        self.i = 0
    def randrange(self, n):
        v = self.i % n
        self.i += 1
        return v


def test_basic_rates_wilson_and_diff():
    """验证基础通过率、Wilson 区间和差值字段。"""
    got = compare_rates([1, 1, 0, 0], [1, 1, 1, 0], CycleRng(), bootstrap_iters=20)
    assert got["old"]["n"] == 4 and got["old"]["passed"] == 2, got
    assert got["new"]["rate"] == 0.75, got
    assert abs(got["diff"] - 0.25) < 1e-9, got
    lo, hi = got["old"]["wilson_ci"]
    assert 0 <= lo <= got["old"]["rate"] <= hi <= 1, got


def test_bootstrap_ci_is_deterministic_with_injected_rng():
    """验证 bootstrap 只使用注入 rng，因此同样 rng 行为得到同样结果。"""
    a = compare_rates([1, 0, 0, 0], [1, 1, 1, 0], CycleRng(), bootstrap_iters=30)
    b = compare_rates([1, 0, 0, 0], [1, 1, 1, 0], CycleRng(), bootstrap_iters=30)
    assert a["bootstrap_ci"] == b["bootstrap_ci"], (a, b)
    assert len(a["bootstrap_ci"]) == 2 and a["bootstrap_ci"][0] <= a["bootstrap_ci"][1], a


def test_significant_when_bootstrap_interval_excludes_zero():
    """验证 bootstrap 差值区间不跨 0 时标记显著。"""
    got = compare_rates([0, 0, 0, 0], [1, 1, 1, 1], CycleRng(), bootstrap_iters=20)
    assert got["significant"] is True, got
    assert got["bootstrap_ci"][0] > 0, got


def test_required_sample_size_increases_for_smaller_delta():
    """验证希望检测的差异越小，粗略所需样本量越大。"""
    big_delta = compare_rates([1, 0] * 10, [1, 1, 0, 0] * 5, CycleRng(), bootstrap_iters=10, min_detectable_delta=0.2)
    small_delta = compare_rates([1, 0] * 10, [1, 1, 0, 0] * 5, CycleRng(), bootstrap_iters=10, min_detectable_delta=0.05)
    assert small_delta["required_n_per_group"] > big_delta["required_n_per_group"], (big_delta, small_delta)
''',
        hidden=r'''class ZeroRng:
    def randrange(self, n):
        return 0


def test_invalid_inputs_raise_value_error():
    """验证空样本、非法取值和非正 bootstrap 次数会抛 ValueError。"""
    for args in [([], [1], ZeroRng()), ([1], [2], ZeroRng()), ([1], [0], ZeroRng(), 0)]:
        try:
            compare_rates(*args)
            assert False, f"应抛出 ValueError: {args}"
        except ValueError:
            pass


def test_bool_values_are_accepted_as_binary_results():
    """验证 bool 样本可按 0/1 处理。"""
    got = compare_rates([True, False], [True, True], ZeroRng(), bootstrap_iters=5)
    assert got["old"]["passed"] == 1 and got["new"]["passed"] == 2, got


def test_alpha_changes_interval_width():
    """验证更小 alpha 会得到更宽的 Wilson 区间。"""
    wide = compare_rates([1, 0] * 20, [1, 0] * 20, ZeroRng(), bootstrap_iters=5, alpha=0.01)
    narrow = compare_rates([1, 0] * 20, [1, 0] * 20, ZeroRng(), bootstrap_iters=5, alpha=0.2)
    wide_width = wide["old"]["wilson_ci"][1] - wide["old"]["wilson_ci"][0]
    narrow_width = narrow["old"]["wilson_ci"][1] - narrow["old"]["wilson_ci"][0]
    assert wide_width > narrow_width, (wide, narrow)
''',
        solution=r'''def compare_rates(old_results, new_results, rng, bootstrap_iters=1000, alpha=0.05, min_detectable_delta=0.05):
    """Compare two pass-rate samples with Wilson and bootstrap confidence intervals."""
    import math
    from statistics import NormalDist

    def clean(values, name):
        vals = list(values)
        if not vals:
            raise ValueError(f"{name} 不能为空")
        out = []
        for value in vals:
            if isinstance(value, bool):
                out.append(1 if value else 0)
            elif value in (0, 1):
                out.append(int(value))
            else:
                raise ValueError(f"{name} 只能包含 0/1/bool")
        return out

    if isinstance(bootstrap_iters, bool) or not isinstance(bootstrap_iters, int) or bootstrap_iters <= 0:
        raise ValueError("bootstrap_iters 必须是正整数")
    if not (0 < alpha < 1):
        raise ValueError("alpha 必须在 0 到 1 之间")
    if min_detectable_delta <= 0:
        raise ValueError("min_detectable_delta 必须为正数")

    old = clean(old_results, "old_results")
    new = clean(new_results, "new_results")
    z = NormalDist().inv_cdf(1 - alpha / 2)

    def wilson(passed, n):
        phat = passed / n
        denom = 1 + z * z / n
        center = (phat + z * z / (2 * n)) / denom
        half = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
        return (max(0.0, center - half), min(1.0, center + half))

    def summary(values):
        n = len(values)
        passed = sum(values)
        rate = passed / n
        return {"n": n, "passed": passed, "rate": rate, "wilson_ci": wilson(passed, n)}

    old_s = summary(old)
    new_s = summary(new)
    diff = new_s["rate"] - old_s["rate"]

    diffs = []
    for _ in range(bootstrap_iters):
        old_passed = sum(old[rng.randrange(len(old))] for _ in range(len(old)))
        new_passed = sum(new[rng.randrange(len(new))] for _ in range(len(new)))
        diffs.append(new_passed / len(new) - old_passed / len(old))
    diffs.sort()

    def percentile(sorted_values, q):
        if len(sorted_values) == 1:
            return sorted_values[0]
        pos = q * (len(sorted_values) - 1)
        lo = math.floor(pos)
        hi = math.ceil(pos)
        if lo == hi:
            return sorted_values[lo]
        weight = pos - lo
        return sorted_values[lo] * (1 - weight) + sorted_values[hi] * weight

    ci = (percentile(diffs, alpha / 2), percentile(diffs, 1 - alpha / 2))
    p_pool = (old_s["passed"] + new_s["passed"]) / (old_s["n"] + new_s["n"])
    z_power = 0.84
    required = math.ceil(2 * p_pool * (1 - p_pool) * (z + z_power) ** 2 / (min_detectable_delta ** 2))

    return {
        "old": old_s,
        "new": new_s,
        "diff": diff,
        "bootstrap_ci": ci,
        "significant": ci[0] > 0 or ci[1] < 0,
        "required_n_per_group": required,
    }
''',
        hints=["Wilson 区间先算 phat，再用 z 和 n 做中心校正。", "bootstrap 每次分别对 old/new 有放回抽样，记录 new_rate-old_rate。", "显著性可以用差值置信区间是否跨 0 判断；样本量估算只需粗略正态近似。"],
        points=["通过率不确定性评估", "Bootstrap 与随机数注入", "样本量粗估和显著性判断"],
        numpy=False,
    ),
]
