# tools

### Skill 调用

可用 Skill 由 Runtime 扫描 `skills/` 目录后注入到 LoopDecider。

调用规则：

- 需要调用能力时，选择 `call_skill`。
- `action_detail.skill_id` 必须使用可用 Skill 目录中的真实 `skill_id`。
- `action_detail.input` 必须符合该 Skill 的输入结构。
- 信息不足时不要编造参数，先选择 `ask_user` 或等待用户补充。

当前主 Agent 预置 Skill：

- `content_extract`：文本提取、摘要、要点整理。

### Worker 调用

可用 Worker 由 Runtime 扫描 `agents/workers/` 目录后注入到 LoopDecider。

调用规则：

- 需要领域 Worker 处理时，选择 `call_agent`。
- `action_detail.worker_id` 必须使用可用 Worker 目录中的真实 `worker_id`。
- `action_detail.task` 是简短任务标题。
- `action_detail.handoff_context` 是给 Worker 的自然语言交接上下文。
- `action_detail.handoff.reason` 说明为什么交给该 Worker。

当前预置 Worker：

- `amap_worker`：处理高德地图、地址、天气、路线规划和出行建议。
