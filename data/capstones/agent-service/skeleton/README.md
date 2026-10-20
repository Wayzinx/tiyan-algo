# 可部署的最小 Agent 服务

这是一个面向 Agent 开发社招准备的项目骨架。你将按 m1 到 m8 逐步实现一个可部署、可观测、可评测的 FastAPI Agent 服务。

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest tests/test_m1_model.py
```

## 里程碑

- m1：模型适配层与 FakeLLM
- m2：工具系统与内置工具
- m3：Agent 主循环
- m4：RAG 与会话记忆
- m5：SQLite 持久化与断点恢复
- m6：JSONL trace 与统计
- m7：FastAPI 服务化与部署
- m8：评测集、评测脚本与复盘报告
