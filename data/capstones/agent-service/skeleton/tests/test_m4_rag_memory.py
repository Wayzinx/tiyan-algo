from agent_service.rag import BM25Retriever, answer_with_citations, group_tool_pairs, split_markdown, trim_memory


def test_markdown_split_keeps_headings_and_limits_size():
    """Markdown 切分会保留标题并控制片段大小。"""
    chunks = split_markdown("# 安装\n先创建环境。\n# 使用\n运行 pytest。", max_chars=20)
    assert [chunk.heading for chunk in chunks] == ["安装", "使用"]
    assert all(chunk.id.startswith("c") for chunk in chunks)


def test_bm25_retriever_returns_relevant_chunk():
    """BM25 检索能把查询匹配到相关片段。"""
    chunks = split_markdown("# RAG\nBM25 检索 markdown 引用。\n# 服务\nFastAPI 提供接口。")
    hit = BM25Retriever(chunks).search("markdown 检索", top_k=1)[0][0]
    assert hit.heading == "RAG"


def test_answer_with_citations_contains_source_ids():
    """答案组装会返回引用 id 和标题。"""
    retriever = BM25Retriever(split_markdown("# 工具\nAgent 可以调用 calculator 工具。"))
    answer = answer_with_citations("calculator", retriever)
    assert "c1" in answer["answer"]
    assert answer["citations"][0]["heading"] == "工具"


def test_trim_memory_respects_budget_and_summarizes():
    """会话记忆超长时会摘要旧消息并保留新消息。"""
    messages = [{"role": "user", "content": "旧消息" * 80}, {"role": "assistant", "content": "中间" * 80}, {"role": "user", "content": "最新问题"}]
    trimmed = trim_memory(messages, token_budget=40, summarize_fn=lambda items: f"{len(items)} 条")
    assert trimmed[0]["role"] == "system"
    assert trimmed[-1]["content"] == "最新问题"


def test_tool_call_pairs_are_not_split():
    """带 tool_calls 的 assistant 消息和对应 tool 结果不能拆散。"""
    messages = [
        {"role": "user", "content": "a" * 200},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "c1"}]},
        {"role": "tool", "tool_call_id": "c1", "content": "result"},
        {"role": "user", "content": "next"},
    ]
    groups = group_tool_pairs(messages)
    assert len(groups[1]) == 2
    trimmed = trim_memory(messages, token_budget=30)
    roles = [msg["role"] for msg in trimmed]
    assert roles == ["assistant", "tool", "user"]
