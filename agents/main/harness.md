# harness

Harness 只评估 `call_skill` 和 `call_agent` 的执行结果。

允许输出的下一状态：

```text
ready_to_plan
missing_params
failed
```

判断原则：

- 如果执行结果足以支持继续生成用户回答，输出 `ready_to_plan`。
- 如果仍缺少关键参数，输出 `missing_params`，并列出缺失字段。
- 如果执行失败且无法通过追问补救，输出 `failed`。
- 不要只按 executor 的 `status` 字段机械映射，要结合用户请求和上下文判断。
