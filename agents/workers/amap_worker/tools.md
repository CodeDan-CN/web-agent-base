# tools

### Skill 调用

可用 Skill 由 Runtime 扫描当前 Worker 的 `skills/` 目录后注入到 LoopDecider。

调用规则：

- 需要调用能力时，选择 `call_skill`。
- `action_detail.skill_id` 必须使用可用 Skill 目录中的真实 `skill_id`。
- `action_detail.input` 必须符合该 Skill 的输入结构。
- 信息不足时不要编造参数，选择 `ask_user`。

### Worker 边界

当前 Worker 不调用其他 Worker Agent。
