# tools

## content_extract_skill

类型：mock skill executor

适用：

- 文本要点提取
- 摘要整理
- 标题或行动项提取

输入建议：

```json
{
  "content": "需要处理的文本",
  "extract_type": "key_points"
}
```

## planning_worker

类型：mock agent executor

适用：

- 学习路线
- 实施方案
- 任务拆解
- 推进计划

输入建议：

```json
{
  "goal": "用户目标",
  "background": "背景信息",
  "constraints": {}
}
```
