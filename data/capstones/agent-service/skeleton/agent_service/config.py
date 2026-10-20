from __future__ import annotations

from pathlib import Path
from typing import Mapping

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Agent 服务配置，支持默认值、YAML 文件和环境变量覆盖。"""

    model: str = "fake"
    base_url: str = "https://example.invalid/v1"
    api_key: str | None = None
    timeout_seconds: float = 10.0
    max_retries: int = 2
    rate_limit_per_minute: int = 60
    trace_path: str = "traces.jsonl"
    api_keys: list[str] = Field(default_factory=lambda: ["dev-key"])


def load_settings(path: str | Path | None = None, env: Mapping[str, str] | None = None) -> Settings:
    """从默认值、可选 YAML 文件和 AGENT_ 前缀环境变量加载配置。"""
    raise NotImplementedError
