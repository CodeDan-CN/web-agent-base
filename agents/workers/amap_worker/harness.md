# harness

## Harness 判断要求

Harness 只评估 Skill 或 Worker 执行结果是否足以让 Loop 继续。

判断原则：

- 如果结果足以继续生成 Worker 结果，进入 `ready_to_plan`。
- 如果缺少必要地址、城市、起终点、出行方式等信息，进入 `missing_params`。
- 如果接口失败且无法通过补充信息继续，进入 `failed`。
- 不要把单个 Skill 的成功机械等同于整个任务完成。
