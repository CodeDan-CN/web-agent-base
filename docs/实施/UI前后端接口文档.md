# UI 前后端接口文档

本文档定义 Agent Base 前端测试台与 FastAPI 后端之间的接口契约。

它只描述接口、请求响应、SSE 和 AG-UI 事件字段，不描述页面视觉和交互布局。

---

## 一、接口边界

Agent Base 是业务 Agent 框架，不提供完整用户系统。

用户身份由接入方业务系统提供。

前端测试台只负责传入 `user_id`，用于验证不同用户之间的会话、事件、摘要和运行状态隔离。

当前接口覆盖：

- Agent 普通运行。
- Agent AG-UI 流式运行。
- 会话创建、查询、更新、删除。
- 会话聊天记录查询。
- AG-UI 中间步骤事件消费。

---

## 二、通用约定

### 2.1 Base URL

本地默认：

```text
http://127.0.0.1:8003
```

前端可以在测试台中配置 Backend URL。

### 2.2 统一响应结构

非流式接口统一返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | number | 业务状态码，成功为 `200` |
| `msg` | string | 响应信息 |
| `data` | any | 响应数据 |

错误响应也使用相同结构。

### 2.3 身份参数

所有会话和运行接口都需要明确用户与 Agent：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `user_id` | string | 是 | 外部业务系统用户 ID，测试台使用预置用户 |
| `agent_id` | string | 否 | 默认 `main`，UI 不建议普通用户选择 worker |
| `session_id` | string | 否 | 会话 ID，不传时运行接口会自动创建 |

---

## 三、Agent 运行接口

### 3.1 普通运行

```http
POST /agent/run
```

用于非流式调用。

请求：

```json
{
  "user_id": "test_user_001",
  "agent_id": "main",
  "session_id": "可选 session id",
  "request_id": "可选 request id",
  "message": "你好",
  "metadata": {}
}
```

响应 `data`：

```json
{
  "request_id": "request id",
  "session_id": "session id",
  "run_id": "run id",
  "state": "completed",
  "answer": "回答内容",
  "need_user_input": false,
  "question": null
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `request_id` | string | 请求 ID |
| `session_id` | string | 会话 ID |
| `run_id` | string | 本次 AgentRun ID |
| `state` | string | 最终 Loop state |
| `answer` | string / null | 最终回答 |
| `need_user_input` | boolean | 是否需要用户补充信息 |
| `question` | string / null | 追问内容 |

### 3.2 AG-UI 流式运行

```http
POST /agent/run/stream
```

用于前端聊天主流程。

请求体与 `/agent/run` 相同。

响应：

```text
Content-Type: text/event-stream
```

每条 SSE：

```text
event: ag-ui
data: {"type":"RUN_STARTED", ...}
```

前端必须按 `data` 中的 JSON 事件驱动 UI 状态。

---

## 四、Session API

### 4.1 创建会话

```http
POST /sessions
```

请求：

```json
{
  "user_id": "test_user_001",
  "agent_id": "main",
  "title": "新会话"
}
```

响应 `data` 为会话详情。

说明：

- `title` 可为空。
- 空标题由后端保存为 `新会话`。
- 前端也可以不提前创建会话，第一次发送消息时由 `/agent/run/stream` 自动创建。

### 4.2 查询会话列表

```http
GET /sessions?user_id={user_id}&agent_id=main
```

响应 `data`：

```json
[
  {
    "session_id": "session id",
    "user_id": "test_user_001",
    "agent_id": "main",
    "title": "路线和天气查询",
    "state": "completed",
    "loop_count": 3,
    "turn_count": 5,
    "last_message": "帮我看一下目的地天气",
    "updated_at": "ISO 时间",
    "created_at": "ISO 时间"
  }
]
```

### 4.3 查询会话详情

```http
GET /sessions/{session_id}?user_id={user_id}&agent_id=main
```

响应 `data`：

```json
{
  "session_id": "session id",
  "user_id": "test_user_001",
  "agent_id": "main",
  "title": "路线和天气查询",
  "state": "completed",
  "loop_count": 3,
  "turn_count": 5,
  "last_message": "帮我看一下目的地天气",
  "updated_at": "ISO 时间",
  "created_at": "ISO 时间",
  "pending_action": null,
  "missing_params": [],
  "conversation_summary": "当前 session 摘要"
}
```

### 4.4 更新会话

```http
PATCH /sessions/{session_id}
```

请求：

```json
{
  "user_id": "test_user_001",
  "agent_id": "main",
  "title": "路线和天气查询"
}
```

响应 `data` 为更新后的会话详情。

当前只支持更新标题。

### 4.5 删除会话

```http
DELETE /sessions/{session_id}?user_id={user_id}&agent_id=main
```

响应 `data`：

```json
{
  "session_id": "session id",
  "deleted": true
}
```

删除为软删除。

软删除后的会话：

- 不再出现在会话列表。
- 不允许继续运行。
- 原始记录保留在数据库中，便于后续审计或恢复设计。

### 4.6 查询会话聊天记录

```http
GET /sessions/{session_id}/turns?user_id={user_id}&agent_id=main
```

响应 `data`：

```json
[
  {
    "turn_id": "turn id",
    "run_id": "run id",
    "event_id": "event id",
    "user_message": "用户消息",
    "assistant_message": "Agent 回复",
    "final_state": "completed",
    "created_at": "ISO 时间"
  }
]
```

说明：

- 返回用户可见对话轮次。
- 不返回内部 Prompt。
- 不返回原始工具响应全量 JSON。

---

## 五、AG-UI 事件契约

### 5.1 通用字段

所有 AG-UI 事件都有基础字段：

```json
{
  "type": "EVENT_TYPE",
  "runId": "当前 AgentRun ID",
  "threadId": "当前 session_id",
  "timestamp": "ISO 时间"
}
```

### 5.2 事件列表

| 事件 | 说明 |
| --- | --- |
| `RUN_STARTED` | Run 开始 |
| `STATE_SNAPSHOT` | 初始状态快照 |
| `STEP_STARTED` | Loop step 开始 |
| `STATE_DELTA` | 状态或阶段变化 |
| `TOOL_CALL_START` | worker / Skill 调用开始 |
| `TOOL_CALL_ARGS` | 调用参数摘要 |
| `TOOL_CALL_END` | worker / Skill 调用结束 |
| `TEXT_MESSAGE_START` | assistant 文本流开始 |
| `TEXT_MESSAGE_CONTENT` | assistant 文本增量 |
| `TEXT_MESSAGE_END` | assistant 文本流结束 |
| `STEP_FINISHED` | Loop step 结束 |
| `RUN_FINISHED` | Run 完成 |
| `RUN_ERROR` | Run 失败 |

### 5.3 事件扩展字段

| 事件 | 字段 |
| --- | --- |
| `STATE_SNAPSHOT` | `snapshot.phase`、`snapshot.state`、`snapshot.label` |
| `STEP_STARTED` | `step.index`、`step.label` |
| `STATE_DELTA` | `delta.phase`、`delta.label` |
| `TOOL_CALL_START` | `toolCallId`、`toolName`、`label` |
| `TOOL_CALL_ARGS` | `toolCallId`、`args` |
| `TOOL_CALL_END` | `toolCallId`、`result.status`、`result.summary`、`result.missingParams` |
| `TEXT_MESSAGE_START` | `messageId`、`role` |
| `TEXT_MESSAGE_CONTENT` | `messageId`、`delta` |
| `TEXT_MESSAGE_END` | `messageId` |
| `STEP_FINISHED` | `step.index`、`step.state` |
| `RUN_FINISHED` | `state`、`label` |
| `RUN_ERROR` | `error.message`、`label` |

### 5.4 phase 枚举

`STATE_SNAPSHOT` 和 `STATE_DELTA` 可能包含 `phase`。

| phase | 说明 |
| --- | --- |
| `understanding` | 正在理解请求 |
| `planning_next` | 正在规划下一步 |
| `need_more_info` | 需要补充信息 |
| `failed` | 无法继续完成 |
| `tool_result_ready` | worker / Skill 结果已返回 |
| `answering` | 正在生成最终回答 |

### 5.5 Loop state 枚举

| state | 说明 |
| --- | --- |
| `new_request` | 新请求 |
| `ready_to_plan` | 已准备继续规划 |
| `missing_params` | 缺少参数 |
| `awaiting_user` | 等待用户补充 |
| `completed` | 完成 |
| `failed` | 失败 |

`awaiting_user` 是正常业务状态，不是错误。

### 5.6 文本流规则

只有 main agent 的 `TEXT_MESSAGE_*` 事件可以生成用户可见最终回答。

worker 的文本输出属于内部领域结果生成过程，不应直接当作最终回答展示。

### 5.7 单次 run 多轮 Loop 规则

同一个 `runId` 内可能出现多轮 Loop。

`正在理解请求` 只应在第一次进入 Loop 时作为可见理解态出现。

后续 Loop 轮次主要通过 `STATE_DELTA`、`TOOL_CALL_START`、`TOOL_CALL_END` 表达进展。

### 5.8 worker 嵌套事件字段

当后端透传 worker 内部状态时，事件需要带来源字段：

```json
{
  "source": "worker",
  "sourceAgentId": "amap_worker",
  "parentRunId": "main run id",
  "parentToolCallId": "main call_agent toolCallId",
  "depth": 1
}
```

main 自身事件：

```json
{
  "source": "main",
  "sourceAgentId": "main",
  "depth": 0
}
```

前端根据 `depth` 处理嵌套层级。

当前只展示两层：

```text
main step
  worker step
```

---

## 六、前端测试用户约定

测试台内置用户：

```text
test_user_001
test_user_002
demo_buyer
demo_operator
```

切换用户时，前端只改变请求中的 `user_id`。

后端不提供：

- 注册。
- 登录。
- 密码。
- 权限。
- 角色管理。

---

## 七、安全与脱敏

接口和 AG-UI 事件不得返回：

- API Key。
- 内部 Prompt 全量内容。
- 原始工具响应全量 JSON。
- 其他用户会话。
- 已软删除会话。

`TOOL_CALL_ARGS` 只允许返回脱敏后的参数摘要。

`TOOL_CALL_END.result.summary` 只返回可展示摘要，不返回完整 raw data。
