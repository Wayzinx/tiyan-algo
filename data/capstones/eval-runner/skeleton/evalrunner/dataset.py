from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


class DatasetValidationError(ValueError):
    """数据集校验失败，包含行号和字段路径。"""

    def __init__(self, errors: list[dict[str, Any]]):
        self.errors = errors
        raise NotImplementedError


@dataclass(frozen=True)
class EvalCase:
    """单条评测用例。"""

    id: str
    input: Any
    expected: Any
    scorers: list[dict[str, Any]]
    tags: list[str]
    difficulty: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    human_label: Any | None = None


def load_dataset(path: str | Path, tags: Iterable[str] | None = None) -> list[EvalCase]:
    """加载 YAML 或 JSONL 数据集，完成 schema 校验、去重和标签筛选。"""
    raise NotImplementedError


def filter_cases(cases: Iterable[EvalCase], tags: Iterable[str] | None = None) -> list[EvalCase]:
    """按标签取交集筛选用例。"""
    raise NotImplementedError


def dataset_fingerprint(cases: Iterable[EvalCase]) -> str:
    """计算数据集版本指纹，顺序无关且内容敏感。"""
    raise NotImplementedError
