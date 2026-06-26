# harness

### 评估对象

Harness 只评估 `call_skill` 和 `call_agent` 的执行结果。

### 允许状态

允许输出的下一状态：

```text
ready_to_plan
missing_params
failed
```

### 判断原则

- 如果执行结果足以支持继续生成用户回答，输出 `ready_to_plan`。
- 如果仍缺少关键参数，输出 `missing_params`，并列出缺失字段。
- 如果执行层已经成功，但结果与用户真实意图不一致，或仍有可通过用户补充修正的歧义，必须输出 `missing_params`，不要输出 `failed`。
- 如果判断为 `missing_params`，尽量给出可直接转述给用户的追问。
- 只有代码执行失败、接口调用失败、链路执行失败或依赖不可用，且用户补充信息也无法补救时，才输出 `failed`。
- 不要只按 executor 的 `status` 字段机械映射，要结合用户请求和上下文判断。
