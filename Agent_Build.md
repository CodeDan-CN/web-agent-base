# Agent_Build.md

本文档是本项目子 Agent 创建 SOP。

以后新增、迁移或调整 worker agent 时，必须先阅读本文档。

---

## 一、Agent 类型

本项目一个工程只包含：

```text
一个 main agent
多个 worker agent
```

main agent：

- 负责理解用户请求。
- 负责判断是否直接回答。
- 负责判断是否调用 Skill 或 worker。
- 负责整合结果并输出最终用户回答。

worker agent：

- 负责某个领域能力。
- 拥有自己的 Agent 资产。
- 拥有自己的 Skill。
- 返回结构化领域结果给 main agent。
- 不直接承担最终用户回答的完整表达。

---

## 二、什么时候创建 worker

适合创建 worker 的情况：

- 某一类能力有独立领域边界。
- 该领域有多个 Skill。
- main agent 直接理解该领域细节会变重。
- 该领域未来可能继续扩展。
- 该领域有独立输入、输出、Harness 评估规则。

示例：

```text
amap_worker
```

不适合创建 worker 的情况：

- 只是一个轻量工具。
- 只是一个通用文本处理能力。
- 没有独立领域边界。
- 只需要一个 Skill 就能表达清楚。

---

## 三、worker 命名规则

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

## 四、worker 目录结构

每个 worker 必须保持和 main agent 一致的资产结构。

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

## 五、worker 资产文件 SOP

### 5.1 SOUL.md

描述 worker 的身份、语气和表达边界。

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
- 返回给 main agent 的结果形态。

### 5.3 Instruction.md

描述 worker 的行为流程。

必须包含：

- 如何判断直接回答还是调用 Skill。
- 如何处理缺参。
- 如何处理 Skill 失败。
- 如何把结果返回 main agent。

### 5.4 tools.md

描述 worker 可用 Skill。

要求：

- 不手写完整 SkillCatalog。
- 可以描述 Skill 使用原则。
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

- 判断 Skill 结果是否足够返回 main agent。
- 判断是否需要继续追问。
- 判断是否失败。

---

## 六、Skill 归属迁移 SOP

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

---

## 七、main agent 适配 SOP

新增 worker 后，需要调整 main agent 资产。

### 7.1 Agent.md

说明 main agent 可以调用 worker。

不要把 worker 内部 Skill 细节写进 main agent。

### 7.2 Instruction.md

增加调度原则：

```text
如果用户请求属于某个 worker 的领域，选择 call_agent，并填写 worker_id。
```

### 7.3 tools.md

描述 worker 使用方式。

示例：

```text
amap_worker：处理地址解析、路线规划、天气查询、行政区域、IP 定位和坐标转换。
```

### 7.4 output.md

要求 main agent 最终回答用户。

main agent 可以使用 worker 结果，但不暴露 worker 内部执行细节。

---

## 八、Worker 调用协议

main agent 调用 worker 时，推荐 ActionDetail：

```json
{
  "worker_id": "amap_worker",
  "input": {
    "task": "用户要完成的领域任务",
    "user_message": "用户原始消息",
    "context": {}
  }
}
```

兼容字段：

```json
{
  "name": "amap_worker"
}
```

第三阶段开始推荐使用 `worker_id`。

worker 返回：

```json
{
  "status": "success",
  "data": {
    "worker_id": "amap_worker",
    "domain_result": {},
    "used_skills": []
  },
  "summary": "worker 执行摘要",
  "missing_params": [],
  "error": null
}
```

---

## 九、amap_worker 创建示例

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

第一批 Skill：

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

main agent 不直接调用这些 Skill。

main agent 只调用：

```text
call_agent(amap_worker)
```

---

## 十、变更检查清单

新增 worker 后必须检查：

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
- [ ] 测试用例覆盖 main → worker → skill。
- [ ] AG-UI 可以展示 worker 调用步骤。
- [ ] 没有为了测试写死用户问题或关键词。

---

## 十一、推荐实施顺序

1. 判断是否真的需要 worker。
2. 确定 `worker_id`。
3. 创建 worker 目录结构。
4. 编写六个 Agent 资产文件。
5. 创建 `prompts/`。
6. 迁移或新增 worker Skill。
7. 调整 main agent 资产。
8. 实现 WorkerLoader。
9. 实现 WorkerRegistry。
10. 实现 WorkerExecutor。
11. 修改 `call_agent` 执行逻辑。
12. 跑 worker 资产测试。
13. 跑 main → worker 链路测试。
14. 跑 AG-UI 流式测试。
