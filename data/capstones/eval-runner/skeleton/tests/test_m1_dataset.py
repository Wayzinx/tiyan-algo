import json

import pytest

from evalrunner.dataset import DatasetValidationError, dataset_fingerprint, filter_cases, load_dataset


def test_m1_loads_yaml_and_filters_tags(tmp_path):
    """可以加载 YAML 用例并按标签筛选。"""
    path = tmp_path / "cases.yaml"
    path.write_text(
        """
cases:
  - id: c1
    input: 1+1
    expected: "2"
    scorers:
      - type: exact
    tags: [math, smoke]
    difficulty: easy
    source: hand
  - id: c2
    input: hello
    expected: world
    scorers:
      - type: contains
    tags: [chat]
    difficulty: medium
    source: hand
""",
        encoding="utf-8",
    )
    cases = load_dataset(path, tags=["math"])
    assert [case.id for case in cases] == ["c1"]
    assert cases[0].scorers == [{"type": "exact"}]


def test_m1_loads_jsonl_with_line_numbers(tmp_path):
    """JSONL 解析错误会报告准确行号。"""
    path = tmp_path / "cases.jsonl"
    good = {"id": "c1", "input": "x", "expected": "x", "scorers": [{"type": "exact"}], "tags": ["a"], "difficulty": "easy", "source": "hand"}
    path.write_text(json.dumps(good, ensure_ascii=False) + "\n{bad json}\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError) as exc:
        load_dataset(path)
    assert "line 2" in str(exc.value)
    assert exc.value.errors[0]["field"] == "$"


def test_m1_schema_errors_include_field(tmp_path):
    """缺必填字段和类型错误会给出字段路径。"""
    path = tmp_path / "cases.yaml"
    path.write_text("- id: 123\n  input: hi\n  tags: bad\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError) as exc:
        load_dataset(path)
    fields = {err["field"] for err in exc.value.errors}
    assert {"expected", "scorers", "difficulty", "source", "id", "tags"}.issubset(fields)


def test_m1_duplicate_ids_are_rejected(tmp_path):
    """重复用例 id 会被拒绝并指出重复字段。"""
    rows = [
        {"id": "same", "input": "a", "expected": "a", "scorers": [{"type": "exact"}], "tags": ["x"], "difficulty": "easy", "source": "hand"},
        {"id": "same", "input": "b", "expected": "b", "scorers": [{"type": "exact"}], "tags": ["x"], "difficulty": "easy", "source": "hand"},
    ]
    path = tmp_path / "cases.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    with pytest.raises(DatasetValidationError) as exc:
        load_dataset(path)
    assert exc.value.errors[0]["field"] == "id"


def test_m1_fingerprint_is_order_independent(tmp_path):
    """数据集指纹对顺序不敏感但对内容敏感。"""
    path = tmp_path / "cases.jsonl"
    rows = [
        {"id": "b", "input": "b", "expected": "b", "scorers": [{"type": "exact"}], "tags": ["x"], "difficulty": "easy", "source": "hand"},
        {"id": "a", "input": "a", "expected": "a", "scorers": [{"type": "exact"}], "tags": ["y"], "difficulty": "easy", "source": "hand"},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    cases = load_dataset(path)
    assert dataset_fingerprint(cases) == dataset_fingerprint(reversed(cases))
    assert [case.id for case in filter_cases(cases, ["y"])] == ["a"]
