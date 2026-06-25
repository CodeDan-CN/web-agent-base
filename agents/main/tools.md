# tools

## Skill 调用

可用 Skill 由 Runtime 扫描 `skills/` 目录后注入到 LoopDecider。

调用规则：

- 需要调用能力时，选择 `call_skill`。
- `action_detail.skill_id` 必须使用可用 Skill 目录中的真实 `skill_id`。
- `action_detail.input` 必须符合该 Skill 的输入结构。
- 信息不足时不要编造参数，先选择 `ask_user` 或等待用户补充。

第二阶段预置 Skill：

- `content_extract`：文本提取、摘要、要点整理。
- `amap_geocode`：高德地址解析。
- `amap_weather`：高德天气查询。
- `amap_direction_driving`：高德驾车路径规划。
- `travel_briefing_formatter`：出行建议格式化。
- `amap_route_weather_plan`：地址解析、路线、天气和出行建议固定链路。

## planning_worker

类型：mock worker executor

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
