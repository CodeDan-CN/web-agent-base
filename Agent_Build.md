# Agent_Build.md

本文档是本项目 worker Agent 创建 SOP。

新增、迁移或调整 worker Agent 时，必须按本文档执行。

当前项目是业务型 Agent 框架：

```text
一个 main agent
多个 worker agent
```

不同业务模块不在同一个工程里继续拆 module。

如果另一个业务模块也需要 Agent 能力，应重新拉取脚手架，独立编写、独立部署。

---

## 一、Agent 类型

### main agent

main agent 负责：

- 理解用户请求。
- 判断是否直接回答。
- 判断是否调用 main 自己的 Skill。
- 判断是否调用 worker。
- 整合 Skill / worker 结果。
- 面向用户生成最终回答。

main agent 不应该：

- 直接持有 worker 私有领域 Skill。
- 替 worker 预判复杂领域缺参。
- 暴露 Runtime、State、Action、Harness、Prompt 等内部实现。

### worker agent

worker agent 负责某个领域能力。

worker agent 拥有：

- 自己的 Agent 资产。
- 自己的 Skill 目录。
- 自己的 Loop。
- 自己的 Harness。
- 自己的 `conversation_turns`。
- 自己的 `conversation_summary`。

worker agent 返回结构化领域结果给 main。

最终用户回答仍由 main agent 生成。

---

## 二、main agent 与 worker agent 的核心差别

main agent 和 worker agent 目录结构一致，Runtime 能力一致，但系统地位不同。

| 维度 | main agent | worker agent |
| --- | --- | --- |
| 入口 | 直接接收外部系统 / 用户请求 | 只通过 main 的 `call_agent` 被调用 |
| 最终回答权 | 拥有最终面向用户回答权 | 不直接生成完整最终用户回答 |
| 核心职责 | 理解请求、调度 Skill / worker、整合结果、最终回答 | 处理某个领域任务，返回结构化领域结果 |
| 领域深度 | 保持轻量，不承载过多领域细节 | 承载某个领域的 Skill、流程和判断规则 |
| Skill 归属 | 只持有通用 Skill 或 main 轻量能力 | 持有领域 Skill、领域链路 Skill、领域格式化 Skill |
| `call_agent` 权限 | 可以调用 worker | 不允许继续调用其他 worker |
| `call_skill` 权限 | 可以调用 main 自己的 Skill | 可以调用 worker 自己的 Skill |
| 缺参处理 | 决定是否向用户追问 | 发现领域缺参后返回缺参问题给 main，由 main 决定如何追问用户 |
| 上下文作用域 | `user_id + main + session_id` | `user_id + worker_id + session_id` |
| 事件关系 | 创建或复用主事件，决定事件状态 | 使用 main 当前 `event_id`，不独立关闭事件 |
| 会话记忆 | 有自己的 `conversation_turns` 和 `conversation_summary` | 有自己的 `conversation_turns` 和 `conversation_summary` |
| 用户可见性 | 用户主要感知 main 的回答 | 用户不应感知 worker 内部执行细节 |

关键原则：

- worker 不是 main 的提示词片段，而是可独立运行的领域 Agent。
- worker 不是普通 Skill，它拥有自己的 Loop、Harness、SkillCatalog 和上下文。
- worker 也不是新的业务模块。不同业务模块应重新拉取脚手架独立部署。
- main 调 worker 时只给轻量 handoff，Runtime 负责补齐上下文包。
- worker 的结果必须回到 main，最终由 main 统一对用户表达。

---

## 三、什么时候创建 worker

适合创建 worker：

- 某一类能力有清晰领域边界。
- 该领域有多个 Skill。
- main 直接理解该领域细节会变重。
- 该领域未来会持续扩展。
- 该领域有独立输出规范和 Harness 判断标准。
- 该领域需要独立维护上下文。

当前示例：

```text
amap_worker
```

不适合创建 worker：

- 只是一个轻量工具。
- 只是一个通用文本处理能力。
- 没有独立领域边界。
- 一个 Skill 就能表达清楚。
- 只是为了绕过 main 的提示词复杂度。

---

## 四、worker 命名规则

`worker_id` 使用小写蛇形命名。

推荐格式：

```text
<domain>_worker
```

示例：

```text
amap_worker
document_worker
search_worker
```

要求：

- 目录名等于 `worker_id`。
- 不使用中文。
- 不使用空格。
- 不使用泛化过度的名字。

---

## 五、worker 目录结构

每个 worker 必须保持和 main agent 一致的资产结构：

```text
agents/workers/<worker_id>/
├── SOUL.md
├── Agent.md
├── Instruction.md
├── tools.md
├── output.md
├── harness.md
├── prompts/
│   ├── fragments.md
│   └── examples.md
└── skills/
    └── <skill_id>/
        ├── SKILL.md
        └── schema.json
```

不新增 `agent.yaml`。

worker 列表通过 `agents/workers/` 目录扫描得到。

Skill 列表通过该 worker 的 `skills/` 目录扫描得到。

---

## 六、worker 资产文件 SOP

### 5.1 SOUL.md

描述 worker 的身份、气质和表达边界。

要求：

- 明确它是领域 worker。
- 不面向用户暴露内部实现。
- 不夸大能力。

### 5.2 Agent.md

描述 worker 的目标、职责和边界。

必须包含：

- worker 领域。
- 能处理什么。
- 不处理什么。
- 返回给 main 的结果形态。

### 5.3 Instruction.md

描述 worker 的行为流程。

必须包含：

- 如何理解 main 交接的任务。
- 如何结合 `session_context` 和 worker 自己的 recent turns。
- 如何判断直接回答还是调用 Skill。
- 如何处理缺参。
- 如何处理 Skill 失败。
- 如何把领域结果返回 main。

### 5.4 tools.md

描述 worker 可用 Skill 的使用原则。

要求：

- 不手写完整 SkillCatalog。
- 可以描述 Skill 使用边界。
- 真实 Skill 列表由 `skills/` 目录扫描得到。

### 5.5 output.md

描述 worker 输出规范。

要求：

- 输出结构化领域结果。
- 不生成最终用户长回答。
- 不暴露内部 State、Action、Prompt、API Key。

### 5.6 harness.md

描述 worker Harness 评估规则。

要求：

- 判断 Skill 结果是否足够返回 main。
- 判断是否需要继续调用 Skill。
- 判断是否需要 main 向用户追问。
- 判断是否失败。

---

## 七、Skill 归属迁移 SOP

创建 worker 时，需要重新判断已有 Skill 归属。

规则：

- 领域 Skill 放入对应 worker。
- 通用 Skill 留在 main。
- 同一个 Skill 不要同时放 main 和 worker。
- worker 私有链路放 worker。
- worker 私有格式化能力放 worker。

以 `amap_worker` 为例：

main 保留：

```text
agents/main/skills/content_extract/
```

迁移到 worker：

```text
agents/workers/amap_worker/skills/amap_geocode/
agents/workers/amap_worker/skills/amap_weather/
agents/workers/amap_worker/skills/amap_route_driving/
agents/workers/amap_worker/skills/travel_briefing_formatter/
agents/workers/amap_worker/skills/amap_route_weather_plan/
```

Skill 创建和修改遵循：

```text
Skill_Build.md
```

---

## 八、main agent 适配 SOP

新增 worker 后，需要调整 main agent 资产。

### 7.1 Agent.md

说明 main 可以调用该 worker。

不要把 worker 内部 Skill 细节写进 main agent。

### 7.2 Instruction.md

增加调度原则：

```text
如果用户请求属于某个 worker 的领域，选择 call_agent。
```

main 不需要替 worker 填完整参数。

main 只需要判断：

- 是否属于该 worker 领域。
- 给 worker 的任务是什么。
- 当前用户话语中有哪些自然语言交接信息。

### 7.3 tools.md

描述 worker 能力范围。

示例：

```text
amap_worker：处理地址解析、路线规划、天气查询、行政区域、IP 定位和坐标转换。
```

### 7.4 output.md

要求 main 最终回答用户。

main 可以使用 worker 结果，但不暴露 worker 内部执行细节。

---

## 九、Worker 调用协议

main 的 LoopDecider 选择 `call_agent` 时，只输出轻量 handoff。

推荐 ActionDetail：

```json
{
  "worker_id": "amap_worker",
  "task": "规划路线并查看目的地天气",
  "handoff_context": "用户从杭州市西湖区文三路出发，目的地是杭州市上城区湖滨银泰，希望开车过去，并查看目的地天气。",
  "handoff": {
    "reason": "请求属于高德地图领域"
  }
}
```

要求：

- 必须使用 `worker_id`。
- `task` 是简短任务标题。
- `handoff_context` 使用自然语言，不要求固定参数 JSON。
- `handoff.reason` 说明交给该 worker 的原因。
- 不让 main 输出完整 `context_package`。

兼容字段：

```json
{
  "name": "amap_worker"
}
```

但新实现统一使用 `worker_id`。

---

## 十、Runtime 自动补全 Worker Task Package

Runtime 会在 `WorkerExecutor` 中补全 Worker Task Package。

main 不需要自己生成这些字段。

当前补全内容包括：

```text
worker_id
task
handoff_context
handoff
context_package.event_id
context_package.user_message
context_package.conversation_summary
context_package.event_history
context_package.parent_session_context
context_package.recent_turns
context_package.retrieved_context
context_package.long_term_memory
context_package.memory_palace_refs
context_package.previous_worker_result
output_contract
```

说明：

- `event_id` 由 Runtime 生成或复用。
- main 和 worker 共享同一个事件 ID。
- `recent_turns` 来自当前 agent 自己的 `conversation_turns`。
- `conversation_summary` 来自当前 agent 自己的 `session_state`。
- `retrieved_context / long_term_memory / memory_palace_refs` 当前允许为空。
- 记忆宫殿和 `memory_manager` 不进入当前业务型 Agent 框架。

---

## 十一、worker 上下文规则

worker 和 main 使用同一个 Runtime 体系。

worker 进入 Loop 前也会得到：

```text
conversation_summary
recent_turns
event_context.event_dialogues
previous_action_result
action_history
available_skills
```

作用域：

```text
user_id + agent_id + session_id
```

因此：

- main 有 main 的 `conversation_turns`。
- worker 有 worker 的 `conversation_turns`。
- main 和 worker 不共享同一组 recent turns。
- main 和 worker 可以共享同一个 `event_id`。
- 同一事件下，main / worker 的事件 summary 按 `agent_id` 分开。

worker 不直接读取其他 worker 的上下文。

worker 不做跨 session 召回。

---

## 十二、worker 执行结果

worker 的 RuntimeResult 会被 `WorkerExecutor` 转换成 main 可消费的 ActionResult。

成功时：

```json
{
  "status": "success",
  "data": {
    "worker_id": "amap_worker",
    "worker_run_id": "...",
    "worker_session_id": "...",
    "worker_state": "completed",
    "worker_answer": "worker 领域结果",
    "worker_question": null,
    "task_package": {}
  },
  "summary": "Worker 已返回处理结果",
  "missing_params": [],
  "error": null
}
```

缺参时：

```json
{
  "status": "missing_params",
  "summary": "Worker 需要补充信息",
  "question": "需要用户补充的问题",
  "missing_params": ["worker_required_information"]
}
```

worker 结果不会直接返回用户。

结果会进入 main Harness，再由 main 继续 Loop。

---

## 十三、amap_worker 当前示例

目标目录：

```text
agents/workers/amap_worker/
```

职责：

- 地址解析。
- 逆地理编码。
- 天气查询。
- 行政区域查询。
- IP 定位。
- 坐标转换。
- 路径规划。
- 路线天气链路。

当前 Skill：

```text
amap_geocode
amap_regeocode
amap_weather
amap_district_search
amap_ip_location
amap_coordinate_convert
amap_route_driving
amap_route_walking
amap_route_transit
amap_route_distance
travel_briefing_formatter
amap_route_weather_plan
```

main 不直接调用这些 Skill。

main 只调用：

```text
call_agent(amap_worker)
```

---

## 十四、新增 worker 测试要求

新增 worker 后至少验证：

- worker 能被 WorkerRegistry 扫描。
- worker Agent 文件能加载。
- worker SkillCatalog 能加载。
- main 能选择 `call_agent`。
- Runtime 能补全 Worker Task Package。
- worker 能独立走 Loop。
- worker 能调用自己的 Skill。
- worker 结果进入 main Harness。
- main 能基于 worker 结果最终回答用户。
- main / worker 的 `conversation_turns` 按 `agent_id` 隔离。
- 同一事件追问时，上下文能接上。
- AG-UI 能展示 worker / Skill 步骤。

---

## 十五、变更检查清单

- [ ] `agents/workers/<worker_id>/` 存在。
- [ ] 六个基础 Agent 文件齐全。
- [ ] `prompts/` 存在。
- [ ] `skills/` 存在。
- [ ] worker 目录名符合命名规范。
- [ ] worker 职责边界清楚。
- [ ] main agent 已增加 worker 调度说明。
- [ ] 领域 Skill 已迁移到 worker。
- [ ] main agent 不再持有 worker 私有 Skill。
- [ ] worker Skill 均符合 `Skill_Build.md`。
- [ ] Worker Task Package 不由 main 手写完整上下文。
- [ ] main / worker 上下文隔离正常。
- [ ] 测试用例覆盖 main → worker → skill → main。
- [ ] AG-UI 可以展示 worker 调用步骤。
- [ ] 没有为了测试写死用户问题或关键词。

---

## 十六、推荐实施顺序

1. 判断是否真的需要 worker。
2. 确定 `worker_id`。
3. 创建 worker 目录结构。
4. 编写六个 Agent 资产文件。
5. 创建 `prompts/`。
6. 迁移或新增 worker Skill。
7. 调整 main agent 资产。
8. 确认 WorkerRegistry 可扫描。
9. 确认 WorkerExecutor 可调用。
10. 跑 worker 资产加载测试。
11. 跑 main → worker → skill 链路测试。
12. 跑上下文隔离和事件追问测试。
13. 跑 AG-UI 流式测试。
