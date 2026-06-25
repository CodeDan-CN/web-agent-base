# Agent.md

本文档是当前 Agent 框架工程的开发协作说明。

后续任何参与本项目的开发 Agent，都必须先阅读本文档

---

## 一、项目定位

本项目是一个单模块 Agent 工程脚手架。

它不是多模块 Agent 平台，也不是全能力通用 Agent 系统。

当前设计目标是：

```text
一个业务模块
  ↓
拉取一份脚手架
  ↓
编写一个 main agent 和多个 worker agent
  ↓
通过 FastAPI 暴露 Agent 能力
  ↓
独立构建和部署
```

一个工程只服务一个业务模块。

如果另一个业务模块也需要 Agent 能力，应重新拉取脚手架，独立编写、独立构建、独立部署。

---

## 二、核心技术栈

| 类型 | 选型 |
| --- | --- |
| 语言 | Python |
| Web 框架 | FastAPI |
| 数据库 | PostgreSQL |
| ORM | Tortoise ORM |
| 运行环境 | conda + requirements.txt |
| 服务启动 | uvicorn |
| 配置入口 | `.env` |

第一版只保留必要配置。

除 `deployment/docker-compose.yaml` 外，不新增其他 YAML 配置文件。

---

## 三、启动与运行

本项目使用 conda 环境运行。

当前建议环境名：

```bash
conda activate agent-base
```

安装依赖：

```bash
pip install -r requirements.txt
```

启动服务：

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8003 --reload
```

本地 PostgreSQL 可以通过部署目录中的 compose 文件启动：

```bash
docker compose -f deployment/docker-compose.yaml up -d postgres
```

---

## 四、目录职责

项目目录以 `docs/技术方案/脚手架设计.md` 为准。

核心目录如下：

```text
agent-base/
├── .env
├── Agent.md
├── app.py
├── requirements.txt
├── docs/
├── web/
├── schema/
├── agents/
├── runtime/
├── utils/
├── exception/
├── deployment/
└── logs/
```

### web/

`web/` 是接口层。

职责：

- 定义 FastAPI 路由。
- 定义请求和响应结构。
- 校验接口入参。
- 调用 Runtime。
- 将 Runtime 输出转换为 HTTP 响应。

`web/` 不写 Agent 推理逻辑，不直接编排 worker，不直接拼装 Prompt。

### schema/

`schema/` 保存数据实体。

目录划分：

```text
schema/
├── db/     # Tortoise ORM Model
└── api/    # Pydantic 请求和响应 DTO
```

`schema/` 只定义结构，不写业务流程。

### agents/

`agents/` 保存 Agent 角色资产。

当前约定：

```text
agents/
├── main/
└── workers/
```

一个模块只能有一个 `main` agent。

可以有多个 worker agent。

Agent 元信息通过目录约定和 Markdown 内容推导，不使用 `agent.yaml`。

### runtime/

`runtime/` 是 Agent 执行核心。

职责：

- 加载 Agent 文件。
- 组装 Context。
- 执行 Agent Loop。
- 调用 Skill。
- 调用 worker。
- 执行 Harness。
- 管理 State。
- 触发 Runtime Hook。

### utils/

`utils/` 放公共工具方法。

它不承载业务主流程，不承载 Agent 决策逻辑。

### exception/

`exception/` 放全局异常和自定义异常。

接口层、Runtime、Skill、worker 的异常应尽量统一从这里抛出或转换。

### deployment/

`deployment/` 放部署文件。

允许包含：

- Dockerfile。
- docker-compose.yaml。
- 部署说明。
- 启动脚本。

### logs/

`logs/` 放本地文件日志。

结构化运行记录不放在 `logs/`，应进入数据库。

---

## 五、详细设计入口

根目录 `Agent.md` 只保留项目级协作规则，不重复展开 Agent 资产、Skill 结构和 Loop 细节。

需要了解具体设计时，按需阅读：

| 主题 | 文档 |
| --- | --- |
| Agent 目录结构、Agent 资产、Skill 结构 | `docs/技术方案/脚手架设计.md` |
| Loop 状态、Action、Runtime、Harness、State Manager | `docs/PRD/Loop 设计优化版本.md` |
| 数据库、API、Runtime Hook、技术实现方案 | `docs/技术方案/技术方案.md` |
| 后续暂缓实现或演进事项 | `docs/技术方案/技术债务.md` |
| 创建或调整 Skill | `Skill_Build.md` |
| 创建或调整 worker agent | `Agent_Build.md` |

实现时必须以这些文档为准。

如果发现文档之间存在冲突，应先修正文档并确认共识，再继续实现。

新增 Skill 必须遵循 `Skill_Build.md`。

新增 worker agent 必须遵循 `Agent_Build.md`。

## 六、开发规则

### 代码分层

不要把整条业务链路堆在一个函数里。

推荐分层：

```text
web → runtime → schema/db
          ↓
       agents / tools / harness / state / context
```

`web/` 只处理 HTTP。

`runtime/` 编排 Agent 闭环。

`schema/` 定义结构。

`agents/` 保存 Agent 资产。

### 方法长度

单个方法应尽量控制在 50 行以内。

超过 80 行需要主动拆分。

超过 100 行必须拆分。

当一个方法同时承担参数校验、状态转换、数据库读写、模型调用、结果组装等多个职责时，必须拆成多个小函数。

### 注释

复杂类和核心方法需要写 docstring。

普通工具函数如果行为清晰，可以保持简洁。

不要写无意义注释。

推荐格式：

```python
class RuntimeEngine:
    """
    Agent Runtime 编排器。

    负责接收一次用户请求，驱动 Context Engineer、LoopDecider、
    ActionExecutor、HarnessEvaluator 和 StateManager 完成闭环。
    """
```

```python
async def run(self, request: AgentRunRequest) -> AgentRunResponse:
    """
    执行一次 Agent 请求。

    Args:
        request: Agent 运行请求。

    Returns:
        Agent 运行结果。
    """
```

### 依赖管理

新增依赖必须写入 `requirements.txt`。

依赖必须固定版本号。

允许：

```text
fastapi==0.115.0
```

不允许：

```text
fastapi
fastapi>=0.115
fastapi~=0.115
```

### 配置管理

第一版只使用 `.env`。

不要新增 `config/database.yaml`。

不要新增 `config/memory.yaml`。

不要新增其他非部署 YAML。

### ORM 与 SQL

常规 CRUD 使用 Tortoise ORM。

不要在业务流程里散落 raw SQL。

---

## 七、Git 规则

除非用户明确要求，否则不得自行执行：

- git commit。
- git push。
- git reset。
- git checkout 回滚用户改动。
- 改写 Git 历史。

如果用户要求 Git 操作，只能执行被明确授权的范围。

不得提交无关文件。

不得回滚非本次任务产生的修改。

---

## 八、协作铁律

1. 不要擅自扩展设计。
2. 不要擅自添加字段。
3. 不要擅自添加目录。
4. 不要擅自引入新中间件。
5. 不要擅自引入新配置文件。
6. 不要用默认值掩盖缺失参数。
7. 不要静默吞掉异常。
8. 不要偷偷重试导致行为不可追踪。
9. 不要让 Hook 失败影响 Agent 主链路。
10. 不要让 `session_state` 承担高频日志职责。
11. 不要为了优化测试或演示效果，在代码中添加规则相关的写死逻辑。
12. 不要为了优化局部效果，在提示词中牺牲通用性或把通用 Agent 写窄。

凡是产品未明确要求、设计文档未明确约定、用户未明确确认的内容，不得自行脑补补全。

如果发现设计需要调整，应先修改文档，确认共识，再进入实现。

---

## 九、阅读顺序

先理解设计，再写代码。
