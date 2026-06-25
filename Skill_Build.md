# Skill_Build.md

本文档是本项目 Skill 创建 SOP。

以后新增、迁移或调整 Skill 时，必须先阅读本文档。

---

## 一、Skill 定位

Skill 是 Agent 或 worker 可调用的能力单元。

Skill 只负责完成一个边界清晰的能力，不负责决定最终如何回复用户。

Skill 执行结果必须结构化，并回到 Agent Loop 和 Harness。

Skill 不直接面向用户输出最终回答。

---

## 二、Skill 归属规则

### 放在 main agent 的 Skill

适合放在 `agents/main/skills/`：

- 当前业务模块通用能力。
- 不属于某个明确领域 worker 的能力。
- main agent 自己需要直接调用的轻量能力。

示例：

```text
agents/main/skills/content_extract/
```

### 放在 worker agent 的 Skill

适合放在 `agents/workers/<worker_id>/skills/`：

- 领域 API。
- 领域链路。
- 只服务该 worker 的格式化或计算能力。

示例：

```text
agents/workers/amap_worker/skills/amap_geocode/
agents/workers/amap_worker/skills/amap_route_weather_plan/
```

### 不允许

- 不把领域 API 同时放在 main 和 worker。
- 不把 API Key 写入 Skill 资产。
- 不通过 Skill 目录动态执行未审计 Python 代码。
- 不为通过测试写死用户问题或业务关键词。

---

## 三、Skill 目录结构

每个 Skill 目录必须保持以下结构：

```text
skills/
└── <skill_id>/
    ├── SKILL.md
    ├── schema.json
    ├── references/
    └── assets/
```

第一版必须包含：

```text
SKILL.md
schema.json
```

`references/` 和 `assets/` 可为空。

不新增 `skill.yaml`。

Skill 列表通过目录扫描得到。

---

## 四、Skill 命名规则

`skill_id` 使用小写蛇形命名。

推荐格式：

```text
<domain>_<capability>
<domain>_<capability>_<mode>
```

示例：

```text
content_extract
amap_geocode
amap_route_driving
amap_route_weather_plan
```

要求：

- 目录名必须等于 `schema.json` 里的 `skill_id`。
- `skill_id` 不使用中文。
- 不使用空格。
- 不使用版本号作为常规后缀，除非同一能力确实并存多个协议版本。

---

## 五、统一输出结构

所有 Skill 必须返回统一结构：

```json
{
  "status": "success",
  "data": {},
  "summary": "执行摘要",
  "missing_params": [],
  "error": null
}
```

状态枚举：

```text
success
partial_success
missing_params
failed
```

说明：

- `data` 保存结构化结果。
- `summary` 给 Harness 和 AG-UI 使用。
- `missing_params` 只放业务缺参字段。
- `error` 保存可追踪错误摘要，不放异常堆栈。

---

## 六、schema.json 基础结构

`schema.json` 必须包含：

```json
{
  "skill_id": "<skill_id>",
  "name": "可读名称",
  "description": "用途说明",
  "executor": {},
  "input_schema": {},
  "output_schema": {}
}
```

要求：

- `executor.type` 必须是 `api`、`code` 或 `chain`。
- `input_schema` 必须是 JSON Schema object。
- `output_schema` 必须校验统一输出结构。
- 必填字段必须写入 `required`。
- 不允许用代码默认值掩盖必填字段缺失。

---

## 七、API Skill SOP

API Skill 适合封装 HTTP / RPC / 外部服务接口。

### 7.1 创建目录

```text
agents/workers/amap_worker/skills/amap_geocode/
├── SKILL.md
└── schema.json
```

### 7.2 编写 SKILL.md

必须说明：

- 用途。
- 适用场景。
- 不适用场景。
- 必填参数。
- 调用注意事项。
- 鉴权信息来自 `.env`，不写入资产。

### 7.3 编写 schema.json

示例：

```json
{
  "skill_id": "amap_geocode",
  "name": "高德地址解析",
  "description": "调用高德地理编码接口，将地址转换为经纬度、adcode 和 citycode。",
  "executor": {
    "type": "api",
    "endpoint": "https://restapi.amap.com/v3/geocode/geo",
    "method": "GET",
    "auth": {
      "type": "query",
      "param": "key",
      "env": "AMAP_WEB_SERVICE_KEY"
    },
    "timeout_ms": 10000,
    "response_mapping": {
      "kind": "amap_geocode"
    }
  },
  "input_schema": {
    "type": "object",
    "properties": {
      "address": {"type": "string"},
      "city": {"type": "string"}
    },
    "required": ["address"],
    "additionalProperties": false
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "status": {"type": "string", "enum": ["success", "partial_success", "missing_params", "failed"]},
      "data": {"type": "object"},
      "summary": {"type": "string"},
      "missing_params": {"type": "array", "items": {"type": "string"}},
      "error": {"type": ["string", "null"]}
    },
    "required": ["status", "data", "summary", "missing_params", "error"],
    "additionalProperties": false
  }
}
```

### 7.4 增加响应映射

如果 API 响应不是统一结构，需要在 `runtime/tools/skill_adapters.py` 中增加 `response_mapping.kind` 对应的转换逻辑。

要求：

- 不把原始响应全量直接返回给用户。
- 不泄露 API Key。
- 网络错误转换为结构化异常或 `failed`。
- 可恢复业务失败返回 `partial_success` 或 `missing_params`。

### 7.5 验证

必须验证：

- 缺少必填字段时返回 `missing_params`。
- 正常响应能通过 output_schema。
- API Key 不出现在 `tool_call.input_payload`。
- API Key 不出现在 AG-UI 事件。

---

## 八、Code Skill SOP

Code Skill 适合本地确定性处理。

示例：

- 文本提取。
- 格式化。
- 轻量计算。
- 模板渲染。

### 8.1 创建 Skill 资产

```text
agents/main/skills/content_extract/
├── SKILL.md
└── schema.json
```

`schema.json` 中 executor：

```json
{
  "executor": {
    "type": "code",
    "name": "content_extract"
  }
}
```

### 8.2 编写本地执行器

代码放在：

```text
runtime/tools/builtin_skills/
```

示例：

```text
runtime/tools/builtin_skills/content_extract.py
```

执行器必须继承或遵循 `BaseCodeSkill`：

```python
class ContentExtractSkill(BaseCodeSkill):
    name = "content_extract"

    async def run(self, payload, context):
        return {
            "status": "success",
            "data": {},
            "summary": "执行完成",
            "missing_params": [],
            "error": None,
        }
```

### 8.3 注册执行器

在：

```text
runtime/tools/builtin_skills/__init__.py
```

注册：

```python
CODE_SKILL_EXECUTORS = {
    ContentExtractSkill.name: ContentExtractSkill,
}
```

### 8.4 限制

- 不从 Skill 资产目录动态 import Python 文件。
- 不执行用户上传代码。
- 不在 Code Skill 里调用未声明外部服务。
- 不把最终回答逻辑写进 Code Skill。

---

## 九、Chain Skill SOP

Chain Skill 适合组合多个已有 Skill，形成稳定业务链路。

示例：

```text
amap_route_weather_plan
```

链路：

```text
amap_geocode
→ amap_geocode
→ amap_route_driving
→ amap_weather
→ travel_briefing_formatter
```

### 9.1 创建 Skill 资产

```text
agents/workers/amap_worker/skills/amap_route_weather_plan/
├── SKILL.md
└── schema.json
```

`schema.json` 中 executor：

```json
{
  "executor": {
    "type": "chain",
    "chain_id": "amap_route_weather_plan"
  }
}
```

### 9.2 编写链路适配器

在：

```text
runtime/tools/skill_adapters.py
```

增加或扩展 ChainSkillAdapter。

要求：

- 每一步调用已有 Skill。
- 每一步结果必须结构化。
- 一步失败时返回结构化失败。
- 不吞掉失败。
- 不绕过 input_schema 和 output_schema。

### 9.3 链路输入

Chain Skill 输入只保留链路真正需要的参数。

必填字段必须来自用户显式输入、会话上下文或上游执行结果。

不要让模型用假设值补齐必填字段。

### 9.4 链路输出

Chain Skill 输出建议包含：

```json
{
  "data": {
    "steps": [],
    "domain_result": {}
  }
}
```

`steps` 用于追踪链路中间结果。

最终用户回答仍由 Agent 生成。

---

## 十、变更检查清单

新增或修改 Skill 后，必须检查：

- [ ] 目录名等于 `skill_id`。
- [ ] `SKILL.md` 非空。
- [ ] `schema.json` 可解析。
- [ ] `executor.type` 正确。
- [ ] `input_schema.required` 合理。
- [ ] `output_schema` 校验统一输出结构。
- [ ] API Key 不进入资产文件。
- [ ] Code Skill 已注册。
- [ ] Chain Skill 每一步都有失败处理。
- [ ] 已补充对应测试用例。
- [ ] 没有为了测试写死用户问题或关键词。

---

## 十一、推荐实施顺序

1. 判断 Skill 应归属 main 还是 worker。
2. 创建 Skill 目录。
3. 编写 `SKILL.md`。
4. 编写 `schema.json`。
5. 根据类型补 Adapter 或 builtin executor。
6. 跑资产加载测试。
7. 跑输入缺参测试。
8. 跑正常调用测试。
9. 跑 Agent Loop 测试。
10. 跑 AG-UI 流式测试。
