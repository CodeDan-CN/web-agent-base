# Agent Base

业务型 Agent 框架样板工程。

本项目用于在一个具体业务模块中快速接入 Agent 能力：

```text
拉取样板工程
  ↓
按业务场景改造 main agent
  ↓
按领域新增或调整 worker agent
  ↓
按能力新增 api / code / chain Skill
  ↓
通过 FastAPI 对外提供 Agent 能力
  ↓
独立构建和部署
```

本项目不是多模块 Agent 平台，也不是个人助手型全能力 Agent 系统。

一个工程只服务一个业务模块。

如果另一个业务模块也需要 Agent 能力，应重新拉取脚手架，独立编写、独立构建、独立部署。

---

## 当前能力

已落地的核心能力：

- FastAPI 接口服务。
- OpenAI-compatible 大模型调用。
- 主 Agent Loop：`decide → execute → harness → state`。
- AG-UI SSE 流式事件输出。
- main agent 与 worker agent 目录扫描。
- Skill 扫描、输入校验、执行、输出校验。
- 三类 Skill：
  - `api`
  - `code`
  - `chain`
- worker agent 闭环：
  - main 调用 worker。
  - worker 复用同一套 Runtime。
  - worker 调用自己的 Skill。
  - worker 结果回到 main Harness。
  - main 生成最终用户回答。
- 事件上下文：
  - `agent_event`
  - `agent_event_run`
  - `agent_event_context`
- 当前 session 上下文压缩：
  - `conversation_turn`
  - `conversation_summary`
  - `recent_turns`
  - `event_dialogues`
  - 精确去重
  - 长会话摘要压缩
- main / worker 上下文按 `user_id + agent_id + session_id` 隔离。
- Hook 失败不阻断主链路。

当前示例 worker：

```text
agents/workers/amap_worker/
```

当前示例领域能力：

- 高德地址解析。
- 高德天气查询。
- 高德路径规划。
- 路线 + 天气组合链路。

---

## 技术栈

| 类型 | 选型 |
| --- | --- |
| 语言 | Python |
| Web 框架 | FastAPI |
| ORM | Tortoise ORM |
| 数据库 | PostgreSQL |
| 模型调用 | OpenAI-compatible API |
| 运行环境 | conda + requirements.txt |
| 配置 | `.env` |
| 流式协议 | AG-UI over SSE |

---

## 目录结构

```text
agent-base/
├── Agent.md                         # 项目级开发协作规则
├── Agent_Build.md                   # worker Agent 创建和调整 SOP
├── Skill_Build.md                   # Skill 创建和调整 SOP
├── app.py                           # FastAPI 入口
├── requirements.txt                 # Python 依赖
├── .env.example                     # 环境变量示例
├── agents/                          # Agent 资产
│   ├── main/                        # 主 Agent
│   └── workers/                     # worker Agent
├── runtime/                         # Agent Runtime 核心
├── schema/                          # API DTO 和 DB Model
├── web/                             # FastAPI 路由层
├── utils/                           # 公共工具
├── exception/                       # 统一异常
├── docs/                            # 设计和实施文档
├── logs/                            # 本地日志目录
└── ui/                              # 简易测试聊天页面
```

说明：

- `web/` 只处理 HTTP，不写 Agent 推理逻辑。
- `runtime/` 编排 Agent Loop、Skill、worker、Harness、State 和 Context。
- `agents/` 只放 Agent 资产，不放 Runtime 代码。
- `schema/db/` 放 Tortoise ORM Model。
- `schema/api/` 放 Pydantic 请求和响应结构。
- `logs/` 只放本地文件日志，结构化运行记录进入数据库。

---

## 快速开始

### 1. 准备 conda 环境

建议环境名：

```bash
conda activate agent-base
```

安装依赖：

```bash
pip install -r requirements.txt
```

### 2. 准备环境变量

复制环境变量文件：

```bash
cp .env.example .env
```

按实际情况填写：

```env
MODEL_PROVIDER=openai_compatible
MODEL_BASE_URL=https://example.com/v1
MODEL_API_KEY=replace-me
MODEL_NAME=replace-me
MODEL_DISABLE_REASONING=true

DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agent_base

MAX_LOOP_STEPS=5
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173

AMAP_WEB_SERVICE_KEY=replace-me
SKILL_API_TIMEOUT_MS=10000
```

会话上下文压缩默认配置：

```env
SESSION_CONTEXT_MAX_TOKENS=6000
SESSION_SUMMARY_TRIGGER_RATIO=0.8
SESSION_SUMMARY_TARGET_AFTER_COMPRESSION_RATIO=0.35
SESSION_RECENT_TURN_MIN_COUNT=4
SESSION_RECENT_TURN_MAX_COUNT=8
SESSION_SUMMARY_TARGET_TOKENS=800
SESSION_TURN_COMPRESS_BATCH_SIZE=6
```

### 3. 准备数据库

当前工程使用 PostgreSQL。

本地需要先创建数据库：

```sql
CREATE DATABASE agent_base;
```

应用启动时会执行：

```python
Tortoise.generate_schemas(safe=True)
```

用于开发期自动创建缺失表。

正式部署时建议补充明确的数据库迁移方案。

### 4. 启动后端服务

```bash
uvicorn app:app --host 0.0.0.0 --port 8003 --reload
```

也可以直接运行：

```bash
python app.py
```

健康检查：

```bash
curl http://127.0.0.1:8003/health
```

期望返回：

```json
{"status":"ok"}
```

### 5. 启动测试 UI

```bash
cd ui
npm start
```

默认访问：

```text
http://127.0.0.1:5173
```

---

## API

### 普通运行

```http
POST /agent/run
```

请求：

```json
{
  "user_id": "user_001",
  "agent_id": "main",
  "session_id": "session_001",
  "request_id": "request_001",
  "message": "你好，你能帮我做什么？",
  "metadata": {}
}
```

响应：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "request_id": "request_001",
    "session_id": "session_001",
    "run_id": "...",
    "state": "completed",
    "answer": "...",
    "need_user_input": false,
    "question": null
  }
}
```

### AG-UI 流式运行

```http
POST /agent/run/stream
```

返回：

```text
Content-Type: text/event-stream
```

每条事件格式：

```text
event: ag-ui
data: {...}
```

### 查询会话状态

```http
GET /session/{session_id}?user_id=user_001&agent_id=main
```

响应包含：

- `state`
- `loop_count`
- `pending_action`
- `missing_params`
- `conversation_summary`

---

## Agent 资产

一个工程只有一个 main agent：

```text
agents/main/
├── SOUL.md
├── Agent.md
├── Instruction.md
├── tools.md
├── output.md
├── harness.md
└── skills/
```

可以有多个 worker agent：

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
```

main agent 和 worker agent 目录结构一致，但系统地位不同：

- main 直接接收用户请求。
- main 拥有最终回答权。
- worker 只通过 main 的 `call_agent` 被调用。
- worker 处理领域任务，结果回到 main。
- main / worker 各自拥有自己的 `conversation_turns` 和 `conversation_summary`。

新增或调整 worker 时，必须阅读：

```text
Agent_Build.md
```

任何业务 Agent 改造，必须先根据 `Agent_Build.md` 判断应调整 main agent、调整 worker agent、新增 worker agent，还是新增 Skill。

---

## Skill 资产

Skill 目录结构：

```text
skills/
└── <skill_id>/
    ├── SKILL.md
    ├── schema.json
    ├── references/
    └── assets/
```

当前支持三类 Skill：

| 类型 | 说明 |
| --- | --- |
| `api` | 封装 HTTP / RPC / 外部服务接口 |
| `code` | 本地确定性处理 |
| `chain` | 多个已有 Skill 的固定链路 |

Skill 统一输出结构：

```json
{
  "status": "success",
  "data": {},
  "summary": "执行摘要",
  "missing_params": [],
  "error": null
}
```

新增或调整 Skill 时，必须阅读：

```text
Skill_Build.md
```

---

## Runtime 闭环

一次 Agent 请求的核心流程：

```text
RuntimeEngine
  ↓
StateManager 读取 / 创建 session_state
  ↓
EventManager 生成 / 复用 event_id
  ↓
ContextAssembler 组装上下文
  ↓
LLMLoopDecider 判断下一步 Action
  ↓
ActionExecutor 执行 answer_user / ask_user / call_skill / call_agent
  ↓
HarnessEvaluator 评估 Skill / worker 结果
  ↓
StateManager 更新状态
  ↓
RuntimeHook 写入运行记录和上下文副作用
```

支持的 Action：

```text
answer_user
ask_user
call_skill
call_agent
```

支持的 State：

```text
new_request
ready_to_plan
missing_params
awaiting_user
completed
failed
```

---

## 上下文机制

当前 session 上下文由四层组成：

```text
conversation_summary
recent_turns
event_dialogues
current_user_message
```

核心规则：

- 每次用户可见对话写入 `conversation_turn`。
- `conversation_turn` 作用域是 `user_id + agent_id + session_id`。
- main 和 worker 的上下文隔离。
- main 和 worker 可以共享同一个 `event_id`。
- 长会话接近预算时压缩较早对话到 `conversation_summary`。
- 最近 4 轮原始对话强保护。
- `recent_turns` 和 `event_dialogues` 按 `turn_id / run_id / sha1` 精确去重。
- `event_id / turn_id / run_id / summary_batch_id` 不进入模型 Prompt。

---

## 数据表

主要表：

| 表 | 作用 |
| --- | --- |
| `session_state` | 会话状态快照 |
| `agent_run` | 单次 Agent Run |
| `agent_run_step` | Loop step 追加记录 |
| `tool_call` | Skill / worker 调用记录 |
| `agent_event` | 事件 |
| `agent_event_run` | 事件与 run 的关联 |
| `agent_event_context` | 单个 Agent 在某个事件下的 summary |
| `conversation_turn` | 用户可见一轮对话 |

---

## 测试建议

开发后至少执行：

```bash
python -m compileall app.py runtime schema utils web exception
```

建议覆盖：

- `/health` 健康检查。
- `/agent/run` 普通对话。
- `/agent/run/stream` AG-UI 流式输出。
- main 直接回答。
- main 调用 Skill。
- main 调用 worker。
- worker 调用自己的 Skill。
- 长会话压缩。
- event follow-up 追问。
- main / worker 上下文隔离。
- Hook 失败不阻断主链路。

第四阶段已验证过的关键链路：

- 短会话不压缩。
- 真实 worker 天气查询。
- 高德路线 + 天气 + 追问。
- 真实模型会话摘要压缩。
- 被压缩历史事件通过 `event_dialogues` 找回。

---

## 重要开发规则

更多规则见：

```text
Agent.md
```

关键约束：

- 不新增 `agent.yaml`。
- 不新增 `skill.yaml`。
- 除 `deployment/docker-compose.yaml` 外，不新增其他 YAML 配置。
- 不为了测试效果在代码中写死业务规则。
- 不为了局部效果把通用 Prompt 写窄。
- 不用默认值掩盖缺失参数。
- 不让 Hook 失败影响 Agent 主链路。
- 不让 `session_state` 承担高频日志职责。
- 不把 API Key 写入 Agent / Skill 资产。
- 不把 worker 私有 Skill 同时放到 main。

---

## 当前边界

当前暂不实现：

- 多业务模块共享同一工程。
- worker 独立部署。
- 记忆宫殿服务。
- `memory_manager` worker。
- 跨用户召回。
- 跨 session 长期记忆召回。
- 外部队列化 Hook。
- ES / OpenSearch / ClickHouse 日志中间件。
- 正式数据库迁移工具。

这些内容记录在：

```text
docs/技术方案/技术债务.md
```

---

## 文档入口

| 文档 | 说明 |
| --- | --- |
| `Agent.md` | 项目级协作规则 |
| `Agent_Build.md` | worker Agent 创建和调整 SOP |
| `Skill_Build.md` | Skill 创建和调整 SOP |
| `docs/技术方案/脚手架设计.md` | 脚手架目录设计 |
| `docs/技术方案/技术方案.md` | 总体技术方案 |
| `docs/技术方案/技术债务.md` | 技术债务 |
| `docs/PRD/Loop 设计优化版本.md` | Loop 设计 |
| `docs/实施/第一阶段详细架构设计.md` | 第一阶段设计 |
| `docs/实施/第二阶段详细架构设计.md` | 第二阶段设计 |
| `docs/实施/第三阶段详细架构设计.md` | 第三阶段设计 |
| `docs/实施/第四阶段详细架构设计.md` | 第四阶段设计 |

---

## 部署状态

当前仓库尚未补齐 `deployment/` 目录。

部署阶段待补：

- `deployment/Dockerfile`
- `deployment/docker-compose.yaml`
- 后端服务启动说明
- PostgreSQL 启动说明
- 环境变量说明
- 生产日志和排查说明

本地开发请先使用 README 中的本地启动方式。
