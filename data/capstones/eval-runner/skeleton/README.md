# Agent 评测 Runner

这是一个面向 AI / Agent 测试开发练习的配置驱动评测工具。学习者会实现数据集加载、Agent 适配、评分、统计、回放、报告、安全对抗和线上回流能力。

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest tests/test_m1_dataset.py
pytest
```

## 命令行示例

```bash
evalrun run configs/sample_config.yaml
evalrun compare reports/a.json reports/b.json
```

## 模块结构

- `evalrunner.dataset`：YAML / JSONL 数据集加载、校验、去重、指纹。
- `evalrunner.agents`：Python 函数、HTTP、FakeAgent 适配器。
- `evalrunner.runner`：并发执行、超时、重试、重复运行。
- `evalrunner.scorers`：输出评分、轨迹断言、评审一致性。
- `evalrunner.analysis`：通过率估计、置信区间、门禁、稳定性。
- `evalrunner.replay`：cassette 录制 / 回放与 badcase 归因。
- `evalrunner.reports`：Markdown / HTML 报告与门禁。
- `evalrunner.security`：提示词注入、泄露检测、越权检测。
- `evalrunner.monitoring`：日志抽样、反馈入库、漂移告警。
