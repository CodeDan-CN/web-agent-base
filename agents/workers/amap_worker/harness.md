# harness

### Harness 判断要求

Harness 只评估 Skill 或 Worker 执行结果是否足以让 Loop 继续。

### 判断原则

- 如果结果足以继续生成 Worker 结果，进入 `ready_to_plan`。
- 如果缺少必要地址、城市、起终点、出行方式等信息，进入 `missing_params`。
- 如果执行层已经成功，但结果与用户真实意图不一致，或当前地址、城市、起终点、出行方式仍存在可补救歧义，必须进入 `missing_params`，不要进入 `failed`。
- 如果进入 `missing_params`，尽量给出主 Agent 可以直接转述给用户的追问。
- 只有代码执行失败、接口调用失败、链路执行失败或依赖不可用，且用户补充信息也无法补救时，才进入 `failed`。
- 不要把单个 Skill 的成功机械等同于整个任务完成。
