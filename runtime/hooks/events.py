from dataclasses import dataclass
from typing import Any


@dataclass
class LoopStepCompletedEvent:
    """
    Loop 步骤完成事件。

    Attributes:
        step_id (str): 步骤 ID。
        run_id (str): 运行 ID。
        session_id (str): 会话 ID。
        step_index (int): 步骤序号。
        state_before (str): 执行前状态。
        action (str): Action。
        action_detail (dict[str, Any]): Action 详情。
        execution_result (dict[str, Any] | None): 执行结果。
        harness_feedback (dict[str, Any] | None): Harness 反馈。
        state_after (str): 执行后状态。
    """

    step_id: str
    run_id: str
    session_id: str
    step_index: int
    state_before: str
    action: str
    action_detail: dict[str, Any]
    execution_result: dict[str, Any] | None
    harness_feedback: dict[str, Any] | None
    state_after: str


@dataclass
class ToolCallCompletedEvent:
    """
    工具调用完成事件。

    Attributes:
        tool_call_id (str): 调用 ID。
        run_id (str): 运行 ID。
        session_id (str): 会话 ID。
        action (str): Action。
        tool_name (str): 工具名称。
        input_payload (dict[str, Any]): 输入。
        output_payload (dict[str, Any]): 输出。
        status (str): 状态。
    """

    tool_call_id: str
    run_id: str
    session_id: str
    action: str
    tool_name: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    status: str


@dataclass
class EventSummaryRequestedEvent:
    """
    事件摘要请求事件。

    Attributes:
        event_id (str): 事件 ID。
        user_id (str): 用户 ID。
        session_id (str): 会话 ID。
        trigger_agent_id (str): 触发摘要的 Agent ID。
        final_state (str): 触发时最终状态。
    """

    event_id: str
    user_id: str
    session_id: str
    trigger_agent_id: str
    final_state: str
