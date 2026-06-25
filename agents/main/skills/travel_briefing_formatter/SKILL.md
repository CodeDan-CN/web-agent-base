# travel_briefing_formatter

## 用途

将路线结果和天气结果组合成结构化出行建议。

## 适用场景

- 上游已经获得路线规划结果。
- 上游已经获得目的地天气结果。
- 用户需要一个可读的出行简报。

## 不适用场景

- 缺少路线或天气结果。

## 调用注意事项

- 必须提供 `origin_address`、`destination_address`、`route` 和 `weather`。
- 输出只作为结构化中间结果，最终回答仍由 Agent 生成。
