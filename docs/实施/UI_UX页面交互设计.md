# UI / UX 页面交互设计

本文档定义 Agent Base 前端测试台的页面结构、组件、状态和交互规则。

接口路径、请求响应和 AG-UI 事件字段见：

```text
docs/实施/UI前后端接口文档.md
```

---

## 一、设计目标

当前 UI 服务业务型 Agent 框架的验证和交付。

它不是营销页，也不是完整业务系统后台。

它应该让接入方清楚验证：

- main agent 是否能正常回答。
- main agent 是否能调用 worker。
- worker 是否能调用 Skill。
- 中间步骤是否完整输出。
- 多轮 session 是否连续。
- 长会话摘要和事件追问是否有效。
- 用户、agent、session 是否隔离。

体验目标：

- 打开就是聊天，不出现 landing page。
- 输入区始终可见。
- 回答流式生成。
- 中间步骤可见但不干扰阅读。
- 简单问题不显得笨重。
- 会话历史可切换。
- 运行失败能清楚提示。

---

## 二、信息架构

桌面端：

```text
┌──────────────────────────────────────────────────────────────┐
│ App Shell                                                    │
│ ┌───────────────┬──────────────────────────────────────────┐ │
│ │ Left Sidebar  │ Chat Workspace                           │ │
│ │               │ ┌──────────────────────────────────────┐ │ │
│ │ Session List  │ │ Top Bar                              │ │ │
│ │ User / Agent  │ ├──────────────────────────────────────┤ │ │
│ │ Settings      │ │ Message Timeline                     │ │ │
│ │               │ │                                      │ │ │
│ │               │ ├──────────────────────────────────────┤ │ │
│ │               │ │ Composer                             │ │ │
│ │               │ └──────────────────────────────────────┘ │ │
│ └───────────────┴──────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

移动端：

```text
┌─────────────────────────────┐
│ Top Bar                     │
├─────────────────────────────┤
│ Message Timeline            │
│                             │
├─────────────────────────────┤
│ Composer                    │
└─────────────────────────────┘

Sidebar 通过抽屉打开。
```

---

## 三、页面结构

### 3.1 App Shell

职责：

- 管理整体布局。
- 管理 sidebar 展开 / 收起。
- 管理响应式断点。

桌面端布局：

```text
sidebar: 280px
chat max-width: 860px 到 960px
height: 100vh
```

移动端：

```text
sidebar: drawer
chat: full width
composer: bottom sticky
```

### 3.2 Left Sidebar

Sidebar 包含：

```text
Brand
New Chat
Session Search
Session List
Test User Switcher
Agent Switcher
Backend Settings
Runtime Status
```

结构：

```text
┌─────────────────────────┐
│ Agent Base              │
│ Business Agent Runtime  │
├─────────────────────────┤
│ + New Chat              │
├─────────────────────────┤
│ Search sessions         │
├─────────────────────────┤
│ Today                   │
│  路线和天气查询          │
│  售后流程设计            │
│                         │
│ Previous                │
│  文本提取测试            │
├─────────────────────────┤
│ User: test_user_001     │
│ Agent: main             │
│ Backend: 127.0.0.1:8003 │
└─────────────────────────┘
```

### 3.3 测试用户切换

UI 不提供真实用户管理。

真实用户体系由接入方业务系统负责。

测试台内置几个用户，用于验证隔离：

```text
test_user_001
test_user_002
demo_buyer
demo_operator
```

切换用户时：

- 当前进行中的 run 必须先结束或取消。
- 清空当前聊天区。
- 重新加载新用户的会话列表。
- 默认选中该用户最近更新的 main agent 会话。
- 如果该用户没有会话，进入空会话页。

UI 不展示注册、登录、密码、权限和角色管理。

### 3.4 会话管理交互

会话是 Agent Runtime 的上下文边界。

前端必须使用后端会话数据作为真实来源，不只依赖浏览器本地缓存。

新建会话：

- 点击 `New Chat`。
- 创建空 timeline。
- Sidebar 增加一个新会话项。
- 输入第一条消息后进入正常聊天。

选择会话：

- 点击 Sidebar 会话项。
- 聊天区清空并加载该会话历史。
- Top Bar 更新会话标题和状态。

删除会话：

- 在会话项菜单中点击删除。
- 二次确认。
- 删除后从 Sidebar 移除。
- 如果删除的是当前会话，切换到最近一个会话。
- 如果没有其他会话，进入空会话页。

更新标题：

- 会话项菜单或 Top Bar 中触发重命名。
- 标题为空时显示 `新会话`。
- 超长标题一行省略，hover 展示完整标题。

`awaiting_user` 会话需要在列表中显示轻量等待标识。

### 3.5 Chat Workspace

Chat Workspace 包含：

```text
Top Bar
Message Timeline
Composer
```

Top Bar 显示当前会话和运行状态。

Message Timeline 显示用户消息、AI 消息和中间步骤。

Composer 负责输入、发送、停止、附件预留。

---

## 四、核心页面

### 4.1 空会话页

打开新会话时，中央显示轻量欢迎状态。

不使用营销式 Hero。

```text
                  Agent Base
        业务 Agent Runtime 测试工作台

  [ 帮我查从文三路到湖滨银泰的路线和天气 ]
  [ 把这段项目说明提炼成要点              ]
  [ 帮我设计一个售后流程草案              ]
  [ 测试多轮补充信息                      ]

              Message Agent Base...
```

要求：

- 不解释系统功能。
- 不展示大段说明。
- 建议问题真实可点。
- 点击建议问题后填入输入框或立即发送。

### 4.2 普通聊天页

消息流结构：

```text
User Message
Assistant Steps
Assistant Message
User Message
Assistant Steps
Assistant Message
```

关键点：

- 用户消息靠右。
- AI 消息靠左或全宽正文。
- 消息区域整体居中。
- 最大阅读宽度 760px 到 860px。
- 不使用卡片套卡片。
- 回答正文支持 Markdown。

### 4.3 执行步骤页

每次 AI 回答前，可以显示一个可折叠步骤区域。

默认：

- 运行中展开。
- 完成后收起或保持用户上次偏好。

视觉：

```text
┌───────────────────────────────────────────────┐
│ 执行步骤                              收起     │
├───────────────────────────────────────────────┤
│ 1. 正在理解请求。                             │
│ 2. 我准备查询路线并查看目的地天气。            │
│ 3. 正在调用 amap_worker。                     │
│ 4. 正在调用 amap_route_weather_plan。          │
│ 5. 已拿到 Skill 结果：驾车约 8.2 公里...       │
│ 6. 正在生成最终回答。                         │
└───────────────────────────────────────────────┘
```

步骤区域不是回答气泡，不覆盖回答正文。

它是 AI 消息流中的独立块。

### 4.4 运行失败页

失败时显示：

```text
请求没有完成

服务暂时无法完成这次请求。你可以稍后重试，或调整输入后再发送。

[重新发送]
```

不暴露：

- Python 堆栈。
- API Key。
- 内部 Prompt。
- 原始工具响应全量 JSON。

调试信息可以进入浏览器 console 或 Debug 面板，不默认展示给业务用户。

---

## 五、组件设计

### 5.1 Sidebar Brand

内容：

```text
Agent Base
Business Agent Runtime
```

图标使用简洁字母标识 `A`。

### 5.2 New Chat Button

位置：sidebar 顶部。

行为：

- 清空当前 timeline。
- 进入空会话状态。
- 下一次发送时继续使用新会话上下文。

文案：

```text
New chat
```

或：

```text
新会话
```

### 5.3 Session List

分组：

```text
Today
Yesterday
Previous 7 days
```

每条显示：

```text
会话标题
最后更新时间
状态标记
```

状态标记：

```text
completed
awaiting_user
failed
```

### 5.4 User / Agent Switcher

字段：

```text
User ID
Agent ID
Backend URL
```

定位：

- 开发和测试入口。
- 生产接入外部系统后可隐藏。

行为：

- 切换 User ID 后，会话列表按用户隔离。
- Agent ID 默认 `main`。
- 不建议普通用户手动选择 worker。

### 5.5 Top Bar

显示：

```text
当前会话标题
运行状态
当前 agent
```

状态示例：

```text
Ready
Thinking
Calling Skill
Streaming
Completed
Awaiting user
Failed
```

右侧操作：

```text
Clear
Export
Session detail
```

### 5.6 Message Bubble

用户消息：

- 右侧。
- 轻微背景色。
- 最大宽度 70% 到 76%。
- 支持换行。

AI 消息：

- 左侧或全宽正文。
- 白色或透明背景。
- 支持 Markdown。
- 支持代码块、列表、表格基础样式。

建议：AI 回答不强制放进重边框气泡，用户消息使用轻量气泡。

### 5.7 Step Panel

字段：

```text
title: 执行步骤
current_state: 当前步骤摘要
items: 步骤列表
open: 是否展开
```

状态样式：

| 状态 | 样式 |
| --- | --- |
| running | 小圆点或 spinner |
| success | check 图标 |
| failed | error 图标 |
| waiting | clock 图标 |

### 5.8 Composer

结构：

```text
┌──────────────────────────────────────────────┐
│ Message Agent Base...                        │
│                                      [Send]  │
└──────────────────────────────────────────────┘
```

行为：

- `Enter` 发送。
- `Shift + Enter` 换行。
- 输入为空不能发送。
- 发送中禁用按钮。
- 流式运行时按钮可变成 `Stop`。
- 错误后可重新发送。

---

## 六、视觉规范

### 6.1 总体风格

关键词：

```text
克制
清晰
高密度但不拥挤
少装饰
强阅读性
```

避免：

- 大面积渐变背景。
- 装饰性光斑。
- 过度卡片化。
- 卡片套卡片。
- 每个区域都加重阴影。

### 6.2 色彩

推荐色板：

```text
Background: #ffffff / #f7f7f8
Sidebar: #f9f9f9
Border: #e5e5e5
Text: #111827
Muted: #6b7280
Accent: #10a37f 或 #0071e3
Error: #dc2626
Warning: #d97706
Success: #059669
```

主色只用于按钮、焦点和状态。

### 6.3 字体

字体栈：

```css
font-family:
  -apple-system,
  BlinkMacSystemFont,
  "SF Pro Text",
  "Segoe UI",
  sans-serif;
```

字号：

| 场景 | 大小 |
| --- | --- |
| 正文 | 15px / 16px |
| 辅助信息 | 12px / 13px |
| 顶部标题 | 14px / 15px |
| 输入框 | 15px / 16px |

不使用 viewport 字体缩放。

letter-spacing 保持 `0`。

### 6.4 间距

```text
sidebar padding: 12px 到 16px
message gap: 16px 到 24px
composer padding: 12px
chat max-width: 860px
```

聊天正文区域：

```text
desktop max-width: 860px
wide max-width: 920px
mobile width: calc(100vw - 32px)
```

### 6.5 圆角

- 页面工具类卡片：8px 到 12px。
- 输入框：16px 到 24px。
- 用户消息气泡：18px 到 22px。
- 不把所有元素都做成大圆角。

---

## 七、AG-UI 展示规则

本节只描述 UI 如何展示 AG-UI 运行过程。

事件字段和协议见接口文档。

### 7.1 顶层步骤展示

允许展示：

```text
正在理解请求。
我准备查询路线并查看目的地天气。
正在调用 amap_worker。
正在调用 amap_route_weather_plan。
已拿到 amap_route_weather_plan 的结果：驾车约 8.2 公里...
正在生成最终回答。
已完成。
```

不展示：

```text
LoopState.NEW_REQUEST
ActionDecision(...)
Harness raw JSON
内部 Prompt
API Key
完整工具响应 JSON
```

### 7.2 单次请求多轮 Loop

同一次用户请求可能经历多轮 Loop。

`正在理解请求` 只在本次 run 第一次进入 Loop 时展示。

后续轮次不再重复展示理解态，改为展示更有信息量的动作：

```text
我会把地图、路线或天气相关部分交给高德 Worker 处理。
正在调用高德 Worker。
Worker 结果已返回，正在组织回答。
正在生成最终回答。
```

### 7.3 worker 嵌套状态展示

main 调用 worker 时，外层 UI 要展示 worker 执行状态，但不能原样铺开 worker 内部所有事件。

展示目标：

```text
main 正在调用哪个 worker
worker 正在做什么领域动作
worker 调用了哪些关键 Skill
worker 是否拿到结果
worker 是否缺参或失败
main 正在基于 worker 结果生成最终回答
```

不展示：

```text
worker 每一轮重复的“正在理解请求”
worker 内部 Loop state 原始值
worker 内部 Harness 原始判断
worker 内部 Prompt
worker 工具原始响应全量 JSON
worker 的内部 answer_user 被误认为最终回答
```

视觉结构：

```text
执行步骤
1. 正在理解请求。
2. 我会把地图、路线或天气相关部分交给高德 Worker 处理。
3. 正在调用高德 Worker
   3.1 Worker 正在处理地图任务
   3.2 正在组合路线和天气 · amap_route_weather_plan
   3.3 已拿到 amap_route_weather_plan 的结果：驾车约 8.2 公里...
   3.4 Worker 领域结果已返回
4. Worker 结果已返回，正在组织回答。
5. 正在生成最终回答。
6. 已完成。
```

嵌套层级最多两层：

```text
main step
  worker step
```

### 7.4 worker 事件过滤体验

外层 UI 应遵循：

- worker 开始：显示 `Worker 正在处理领域任务`。
- worker planning：展示 worker 的下一步安排。
- worker call skill：显示正在调用的能力。
- worker skill result：显示能力结果摘要。
- worker missing params：显示 `Worker 需要补充信息`。
- worker failed：显示 `Worker 无法完成该领域任务`。
- worker completed：显示 `Worker 领域结果已返回`。

核心规则：

- main 的最终回答才进入用户可见回答区。
- worker 的内部回答不直接变成最终回答气泡。
- worker 的 Skill 调用可以进入步骤栏。
- worker 的参数和原始工具结果默认不展开。

### 7.5 步骤面板折叠规则

运行中：

```text
默认展开
```

完成后：

```text
默认保持展开 1 秒，然后按用户偏好决定是否收起
```

---

## 八、状态设计

### 8.1 Ready

- 输入框可用。
- Send 可点击。
- Top Bar 显示 `Ready`。

### 8.2 Thinking

- Send 禁用或变 Stop。
- Top Bar 显示正在处理。
- 步骤栏创建。

### 8.3 Calling Tool

- 步骤栏显示正在调用的 worker / Skill。
- 如果有 tool name，展示 tool name。
- 不显示原始参数。

### 8.4 Streaming

- AI 回答块出现。
- 文本逐段追加。
- Composer 仍禁用发送。

### 8.5 Awaiting User

- AI 显示追问。
- Composer 恢复可输入。
- Top Bar 显示 `需要补充信息`。
- session 状态标记为 `awaiting_user`。

### 8.6 Failed

- AI 显示失败提示。
- Composer 恢复。
- Top Bar 显示 `Failed`。
- 提供重新发送入口。

---

## 九、业务测试场景

UI 应内置建议问题，用来覆盖当前工程能力。

```text
你好，你能帮我做什么？
```

```text
帮我把这段内容提炼成要点：第四阶段已经实现 conversation_turn、recent_turns 和会话摘要压缩。
```

```text
帮我查一下杭州市上城区湖滨银泰今天的天气。
```

```text
帮我查一下从杭州市西湖区文三路到杭州市上城区湖滨银泰的驾车路线，并顺便看一下目的地天气。
```

```text
回到刚才那个路线问题，目的地是哪儿？天气结果也再说一下。
```

```text
基于我刚才说的售后流程资料，帮我整理一个流程草案。
```

---

## 十、响应式设计

### 10.1 Desktop

宽度大于 1024px：

```text
sidebar 固定展示
chat 居中
composer 固定底部
```

### 10.2 Tablet

宽度 768px 到 1024px：

```text
sidebar 可收起
chat 占满剩余区域
topbar 显示菜单按钮
```

### 10.3 Mobile

宽度小于 768px：

```text
sidebar 变抽屉
message max-width 100%
用户气泡不超过 86%
composer sticky bottom
步骤栏默认收起
```

移动端输入区：

- 避免被键盘遮挡。
- Send 按钮保持可点击。
- 文本过长时输入框最多 120px 高。

---

## 十一、页面草图

### 11.1 桌面版

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ ┌──────────────────────┐ ┌─────────────────────────────────────────────────┐ │
│ │ Agent Base           │ │ 售后流程设计                         Ready      │ │
│ │ Business Runtime     │ ├─────────────────────────────────────────────────┤ │
│ │                      │ │                                                 │ │
│ │ + New chat           │ │                         ┌─────────────────────┐ │ │
│ │                      │ │                         │ 用户消息             │ │ │
│ │ Search sessions      │ │                         └─────────────────────┘ │ │
│ │                      │ │ ┌─────────────────────────────────────────────┐ │ │
│ │ Today                │ │ │ 执行步骤                             收起   │ │ │
│ │  路线天气查询        │ │ │ 1. 正在理解请求。                         │ │ │
│ │  售后流程草案        │ │ │ 2. 正在调用 amap_worker。                 │ │ │
│ │                      │ │ └─────────────────────────────────────────────┘ │ │
│ │ Settings             │ │                                                 │ │
│ │ User: test_user_001  │ │ AI 正文回答，支持 Markdown、列表、代码块。       │ │
│ │ Agent: main          │ │                                                 │ │
│ │ Backend: 8003        │ ├─────────────────────────────────────────────────┤ │
│ │                      │ │ Message Agent Base...                  Send     │ │
│ └──────────────────────┘ └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 移动版

```text
┌──────────────────────────────┐
│ ☰  Agent Base        Ready   │
├──────────────────────────────┤
│                              │
│              用户消息         │
│                              │
│ 执行步骤               展开   │
│                              │
│ AI 正文回答                   │
│                              │
├──────────────────────────────┤
│ Message...            Send   │
└──────────────────────────────┘
```

---

## 十二、完整实现范围

完整 UI 需要实现：

- 左侧 sidebar。
- 新会话。
- 会话列表。
- 测试用户 / agent / backend 设置。
- 中央聊天 timeline。
- AG-UI SSE 全量事件消费。
- 中间步骤折叠栏。
- Markdown 基础渲染。
- Stop。
- 重新发送。
- 复制回答。
- 导出会话。
- Session detail。
- Run 基础耗时展示。
- Tool / Worker 调用摘要展示。
- 发送中状态。
- 错误状态。
- session_id 持久化。
- 建议问题。
- 移动端适配。

不纳入当前 UI 设计：

- 文件上传。
- 图片输入。
- 多模型切换。
- 语音输入。
- 用户登录。
- Prompt 调试面板。
- 深色模式。

---

## 十三、验收标准

UI 完成后应满足：

- 打开页面即可聊天。
- 简单问答首 token 体感快速出现。
- 流式文本正常追加。
- 中间步骤不覆盖最终回答。
- worker / Skill 调用能在步骤栏看到。
- 已拿到 Skill 结果时有明确提示。
- 多轮 session 能连续。
- 新会话能隔离旧上下文。
- 切换测试用户后会话互不串联。
- 错误状态可理解。
- 移动端不出现布局重叠。
- 文本不溢出按钮、气泡、步骤栏。
- 不暴露内部 Prompt、API Key、原始工具响应全量 JSON。
