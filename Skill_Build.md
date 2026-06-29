# Skill_Build.md

本文档是本项目 Skill 创建 SOP。

新增、迁移或调整 Skill 时，必须按本文档执行。

本项目当前已支持三类 Skill：

```text
api
code
chain
```

Skill 只负责完成边界清晰的能力，不负责面向用户生成最终回答。

Skill 执行结果必须结构化，并回到 Agent Loop 和 Harness。

---

## 一、Skill 定位

Skill 是 Agent / worker 可调用的能力单元。

它适合承载：

- 外部 API 调用。
- 本地确定性代码处理。
- 多个 Skill 组成的稳定链路。

它不适合承载：

- Agent 身份、语气、行为准则。
- 最终用户回答的完整表达。
- 用户长期记忆。
- 未审计的动态代码。
- 为了测试效果写死的问题关键词或规则。

---

## 二、Skill 归属规则

### main Skill

放在：

```text
agents/main/skills/
```

适合：

- 当前业务模块通用能力。
- 不属于某个明确领域 worker 的能力。
- main 自己需要直接调用的轻量能力。

当前示例：

```text
agents/main/skills/content_extract/
```

### worker Skill

放在：

```text
agents/workers/<worker_id>/skills/
```

适合：

- 领域 API。
- 领域内固定链路。
- 只服务该 worker 的格式化、计算、转换能力。

当前示例：

```text
agents/workers/amap_worker/skills/amap_geocode/
agents/workers/amap_worker/skills/amap_weather/
agents/workers/amap_worker/skills/amap_route_weather_plan/
```

### 归属原则

- 领域 Skill 只放到对应 worker。
- main 不直接持有 worker 私有 Skill。
- 同一个 Skill 不要同时放 main 和 worker。
- API Key 不写入 Skill 资产。
- Skill 资产目录不存放可动态执行的 Python 代码。

---

## 三、目录结构

每个 Skill 目录保持一致：

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

## 四、命名规则

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

- 目录名必须等于 `schema.json` 中的 `skill_id`。
- 不使用中文。
- 不使用空格。
- 不用版本号作为常规后缀，除非同一能力确实并存多个协议版本。

---

## 五、SKILL.md 编写规则

`SKILL.md` 给 Agent / worker 理解 Skill 使用边界。

必须写清：

- 用途。
- 适用场景。
- 不适用场景。
- 必填参数。
- 可选参数。
- 调用注意事项。
- 失败或缺参时的处理方式。

不写：

- API Key。
- 内部密钥。
- 大段无关接口文档。
- 最终用户回答模板。
- 为某个测试问题特制的关键词规则。

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
- `input_schema.required` 必须准确描述业务必填参数。
- `output_schema` 必须校验统一输出结构。
- 不允许用代码默认值掩盖必填字段缺失。

`SkillDefinition.to_catalog_item()` 会把以下信息注入 LoopDecider：

```text
skill_id
name
description
executor_type
required_input
optional_input
input_fields
```

因此 `description` 和字段 `description` 要写得足够清楚。

---

## 七、统一输出结构

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

字段说明：

| 字段 | 说明 |
| --- | --- |
| `status` | 执行状态 |
| `data` | 结构化业务结果 |
| `summary` | 给 Harness、AG-UI、上层 Agent 使用的简短摘要 |
| `missing_params` | 缺少的业务参数 |
| `error` | 可追踪错误摘要，不放异常堆栈 |

Skill 结果不直接返回用户。

最终回答由 Agent 的 `answer_user` 生成。

---

## 八、API Skill SOP

API Skill 适合封装 HTTP / RPC / 外部服务接口。

### 8.1 创建目录

```text
agents/workers/amap_worker/skills/amap_geocode/
├── SKILL.md
└── schema.json
```

### 8.2 编写 executor

示例：

```json
{
    "executor": {
      "type": "api",
      "base_url_env": "AMAP_WEB_SERVICE_BASE_URL",
      "endpoint": "/v3/geocode/geo",
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
  }
}
```

当前 `ApiSkillAdapter` 支持：

```text
GET
POST
PUT
DELETE
query auth
base_url_env + endpoint
path_params
body_context_fields
response_mapping.kind
```

API Skill 必须使用 `base_url_env + endpoint` 组装完整请求地址：

```json
{
  "executor": {
    "type": "api",
    "base_url_env": "BUSINESS_API_BASE_URL",
    "endpoint": "/v1/nodes/{node_id}",
    "method": "PUT"
  }
}
```

路径模板参数通过 `path_params` 声明。

如果参数来自 Skill 输入：

```json
{
  "path_params": ["node_id"]
}
```

如果参数来自 Runtime context：

```json
{
  "path_params": {
    "node_id": "request.metadata.node_id"
  }
}
```

路径参数在组装 URL 后会从 query/body 参数中消费，不会重复进入请求参数。

`body_context_fields` 用于从 Runtime context 注入 body 字段：

```json
{
  "body_context_fields": {
    "user_id": "request.user_id",
    "session_id": "request.session_id",
    "source_system": "request.metadata.source_system"
  }
}
```

当 `path_params` 或 `body_context_fields` 依赖的字段缺失时，Adapter 必须返回统一 `missing_params` 结果，不抛业务异常，也不把这些字段留给模型自由填写。

当前已实现的高德映射：

```text
amap_geocode
amap_weather
amap_route_driving
amap_generic
backend_envelope
```

`backend_envelope` 用于映射业务系统常见的 `BaseResponse{code,msg,data}`：

```json
{
  "response_mapping": {
    "kind": "backend_envelope",
    "success_code": 200
  }
}
```

如业务系统字段名不同，可以声明：

```json
{
  "response_mapping": {
    "kind": "backend_envelope",
    "code_field": "code",
    "msg_field": "msg",
    "data_field": "data",
    "success_codes": [0, 200]
  }
}
```

如果新增 API 响应结构无法直接使用，需要在：

```text
runtime/tools/skill_adapters.py
```

补充新的 `response_mapping.kind`。

### 8.3 API Skill 要求

- 鉴权来自 `.env`。
- API Key 不进入 `SKILL.md`、`schema.json`、`tool_call.input_payload`、AG-UI 事件。
- 外部接口失败要转成统一结构。
- 可恢复业务失败返回 `partial_success` 或 `missing_params`。
- 不把原始响应全量交给最终用户。

---

## 九、Code Skill SOP

Code Skill 适合本地确定性处理。

示例：

- 文本提取。
- 格式化。
- 轻量计算。
- 模板渲染。

### 9.1 创建 Skill 资产

```text
agents/main/skills/content_extract/
├── SKILL.md
└── schema.json
```

`schema.json` 中：

```json
{
  "executor": {
    "type": "code",
    "name": "content_extract"
  }
}
```

### 9.2 编写内置执行器

代码放在：

```text
runtime/tools/builtin_skills/
```

示例：

```text
runtime/tools/builtin_skills/content_extract.py
runtime/tools/builtin_skills/travel_briefing_formatter.py
```

执行器必须遵循 `BaseCodeSkill`：

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

### 9.3 注册执行器

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

### 9.4 Code Skill 限制

- 不从 Skill 资产目录动态 import Python 文件。
- 不执行用户上传代码。
- 不在 Code Skill 里调用未声明的外部服务。
- 不把最终回答逻辑写进 Code Skill。

---

## 十、Chain Skill SOP

Chain Skill 适合组合多个已有 Skill，形成稳定业务链路。

当前示例：

```text
amap_route_weather_plan
```

链路：

```text
amap_geocode(origin)
→ amap_geocode(destination)
→ amap_route_driving
→ amap_weather
→ travel_briefing_formatter
```

### 10.1 创建 Skill 资产

```text
agents/workers/amap_worker/skills/amap_route_weather_plan/
├── SKILL.md
└── schema.json
```

`schema.json` 中：

```json
{
  "executor": {
    "type": "chain",
    "chain_id": "amap_route_weather_plan"
  }
}
```

### 10.2 编写链路适配器

当前 Chain Skill 由：

```text
runtime/tools/skill_adapters.py
```

中的 `ChainSkillAdapter` 执行。

新增 chain 时需要：

- 增加 `chain_id` 分支。
- 每一步通过 `execute_by_skill_id()` 调用已有 Skill。
- 每一步仍走输入校验、输出校验和统一 ActionResult 转换。
- 一步失败时返回结构化失败。
- 不吞掉失败。

### 10.3 Chain 输入输出

输入只保留链路真正需要的参数。

必填字段必须来自：

- 用户显式输入。
- 当前 session context。
- event dialogues。
- previous_action_result。
- action_history。
- 上游 Skill 输出。

输出建议：

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

## 十一、测试要求

新增或修改 Skill 后至少验证：

- SkillRegistry 能扫描加载。
- `schema.json` 可解析。
- `input_schema` 缺参时返回 `missing_params`。
- 正常输入能返回统一输出结构。
- 输出能通过 `output_schema`。
- `tool_call` 可写入。
- Harness 能消费 Skill 结果。
- AG-UI 能展示 Skill 调用步骤。
- API Key 不泄露。
- 没有为了测试写死用户问题或关键词。

领域 Skill 还需要跑：

```text
main → worker → skill → Harness → main answer_user
```

---

## 十二、变更检查清单

- [ ] 目录名等于 `skill_id`。
- [ ] `SKILL.md` 非空且边界清晰。
- [ ] `schema.json` 可解析。
- [ ] `executor.type` 正确。
- [ ] `input_schema.required` 合理。
- [ ] `output_schema` 校验统一输出结构。
- [ ] API Key 不进入资产文件。
- [ ] API Skill 有 response mapping 或可接受通用映射。
- [ ] Code Skill 已注册。
- [ ] Chain Skill 每一步都有失败处理。
- [ ] 已补充测试用例。
- [ ] 未在代码或提示词中为测试效果写死规则。

---

## 十三、推荐实施顺序

1. 判断 Skill 应归属 main 还是 worker。
2. 判断 Skill 类型：`api / code / chain`。
3. 创建 Skill 目录。
4. 编写 `SKILL.md`。
5. 编写 `schema.json`。
6. 根据类型补 Adapter 或 builtin executor。
7. 跑资产加载测试。
8. 跑输入缺参测试。
9. 跑正常调用测试。
10. 跑 Agent Loop 测试。
11. 跑 AG-UI 流式测试。
