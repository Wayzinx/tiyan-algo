from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence


@dataclass
class Chunk:
    """Markdown 切分后的片段。"""

    id: str
    text: str
    heading: str


def split_markdown(markdown: str, *, max_chars: int = 500) -> list[Chunk]:
    """按标题和长度切分 Markdown，并保留引用所需的标题。"""
    raise NotImplementedError


class BM25Retriever:
    """轻量 BM25 检索器，用于离线 RAG 测试。"""

    def __init__(self, chunks: Sequence[Chunk], *, k1: float = 1.5, b: float = 0.75) -> None:
        """建立倒排统计。"""
        raise NotImplementedError

    def search(self, query: str, *, top_k: int = 3) -> list[tuple[Chunk, float]]:
        """返回 top_k 个片段及分数。"""
        raise NotImplementedError


def answer_with_citations(question: str, retriever: BM25Retriever, *, top_k: int = 2) -> dict[str, object]:
    """根据检索片段组装带引用的答案。"""
    raise NotImplementedError


def count_tokens(message: dict[str, object]) -> int:
    """近似计算单条消息 token 数。"""
    raise NotImplementedError


def group_tool_pairs(messages: Sequence[dict[str, object]]) -> list[list[dict[str, object]]]:
    """将 assistant tool_calls 与紧随的 tool 结果作为不可拆分组。"""
    raise NotImplementedError


def trim_memory(messages: Sequence[dict[str, object]], *, token_budget: int, summarize_fn: Callable[[Sequence[dict[str, object]]], str] | None = None) -> list[dict[str, object]]:
    """按 token 预算裁剪会话记忆，超长时可摘要压缩，且不拆散工具调用配对。"""
    raise NotImplementedError
