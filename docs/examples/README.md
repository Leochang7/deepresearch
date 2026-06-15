# Sample Reports

此目录存放脱敏后的真实运行样例。

## 归档方式

从真实 benchmark run 中选择效果最好的 case：

```bash
# 复制 report（脱敏：去除内部 ID、密钥相关内容）
cp outputs/<run-id>/report.md docs/examples/sample-report.md

# 复制 evaluation
cp outputs/<run-id>/evaluation.json docs/examples/sample-evaluation.json

# 复制 benchmark summary
cp outputs/bench-*/summary.json docs/examples/sample-bench-summary.json
```

## 注意事项

- **不要提交 trace.jsonl 全量文件**（可能包含敏感信息）
- **不要提交包含 API key 的 .env 文件**
- **不要提交 memory_snapshot.jsonl**（可能包含大量向量数据）
- 只提交 report.md、evaluation.json、summary.json

## 已归档样例

（待真实 run 完成后填入）
