from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from runtime.models import ActionDecision, ActionResult, HarnessFeedback
from runtime.state.types import LoopAction, LoopState

AGUIEmit = Callable[[dict[str, Any]], Awaitable[None]]


class AGUIEventAdapter:
    """
    AG-UI 事件适配器。

    Attributes:
        emit_callback (AGUIEmit | None): 事件输出回调。
    """

    def __init__(self, emit_callback: AGUIEmit | None = None) -> None:
        """
        初始化 AG-UI 事件适配器。

        Args:
            emit_callback (AGUIEmit | None): 事件输出回调。
        """
        self.emit_callback = emit_callback

    async def emit(self, event: dict[str, Any]) -> None:
        """
        输出事件。

        Args:
            event (dict[str, Any]): AG-UI 事件。
        """
        if self.emit_callback:
            await self.emit_callback(event)

    def run_started(self, run_id: str, thread_id: str) -> dict[str, Any]:
        """
        构建 RUN_STARTED 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。

        Returns:
            dict[str, Any]: AG-UI 事件。
        """
        return self._base("RUN_STARTED", run_id, thread_id)

    def state_snapshot(
        self,
        run_id: str,
        thread_id: str,
        state: LoopState,
    ) -> dict[str, Any]:
        """
        构建 STATE_SNAPSHOT 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            state (LoopState): 当前状态。

        Returns:
            dict[str, Any]: AG-UI 事件。
        """
        event = self._base("STATE_SNAPSHOT", run_id, thread_id)
        event["snapshot"] = {
            "phase": "understanding",
            "state": state.value,
            "label": "正在理解请求",
        }
        return event

    def step_started(
        self,
        run_id: str,
        thread_id: str,
        step_index: int,
    ) -> dict[str, Any]:
        """
        构建 STEP_STARTED 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            step_index (int): 步骤序号。

        Returns:
            dict[str, Any]: AG-UI 事件。
        """
        event = self._base("STEP_STARTED", run_id, thread_id)
        event["step"] = {"index": step_index, "label": "正在理解请求"}
        return event

    def planning_next(
        self,
        run_id: str,
        thread_id: str,
        decision: ActionDecision,
    ) -> dict[str, Any]:
        """
        构建下一步安排事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            decision (ActionDecision): Action 决策。

        Returns:
            dict[str, Any]: AG-UI 事件。
        """
        event = self._base("STATE_DELTA", run_id, thread_id)
        event["delta"] = {
            "phase": "planning_next",
            "label": self._planning_label(decision),
        }
        return event

    def tool_call_start(
        self,
        run_id: str,
        thread_id: str,
        tool_call_id: str,
        decision: ActionDecision,
    ) -> dict[str, Any]:
        """
        构建 TOOL_CALL_START 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            tool_call_id (str): Tool Call ID。
            decision (ActionDecision): Action 决策。

        Returns:
            dict[str, Any]: AG-UI 事件。
        """
        event = self._base("TOOL_CALL_START", run_id, thread_id)
        event["toolCallId"] = tool_call_id
        event["toolName"] = self._tool_name(decision)
        event["label"] = self._tool_label(decision)
        return event

    def tool_call_args(
        self,
        run_id: str,
        thread_id: str,
        tool_call_id: str,
        decision: ActionDecision,
    ) -> dict[str, Any]:
        """
        构建 TOOL_CALL_ARGS 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            tool_call_id (str): Tool Call ID。
            decision (ActionDecision): Action 决策。

        Returns:
            dict[str, Any]: AG-UI 事件。
        """
        event = self._base("TOOL_CALL_ARGS", run_id, thread_id)
        event["toolCallId"] = tool_call_id
        event["args"] = self._summarize_args(decision.action_detail.get("input") or {})
        return event

    def tool_call_end(
        self,
        run_id: str,
        thread_id: str,
        tool_call_id: str,
        result: ActionResult,
    ) -> dict[str, Any]:
        """
        构建 TOOL_CALL_END 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            tool_call_id (str): Tool Call ID。
            result (ActionResult): Action 结果。

        Returns:
            dict[str, Any]: AG-UI 事件。
        """
        event = self._base("TOOL_CALL_END", run_id, thread_id)
        event["toolCallId"] = tool_call_id
        event["result"] = {
            "status": result.status,
            "summary": result.summary,
            "missingParams": result.missing_params,
        }
        return event

    def harness_delta(
        self,
        run_id: str,
        thread_id: str,
        decision: ActionDecision,
        feedback: HarnessFeedback | None,
    ) -> dict[str, Any]:
        """
        构建 Harness 后状态变化事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            decision (ActionDecision): Action 决策。
            feedback (HarnessFeedback | None): Harness 反馈。

        Returns:
            dict[str, Any]: AG-UI 事件。
        """
        event = self._base("STATE_DELTA", run_id, thread_id)
        event["delta"] = self._feedback_delta(decision, feedback)
        return event

    def text_message_start(self, run_id: str, thread_id: str, message_id: str) -> dict:
        """
        构建 TEXT_MESSAGE_START 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            message_id (str): Message ID。

        Returns:
            dict: AG-UI 事件。
        """
        event = self._base("TEXT_MESSAGE_START", run_id, thread_id)
        event["messageId"] = message_id
        event["role"] = "assistant"
        return event

    def text_message_content(
        self,
        run_id: str,
        thread_id: str,
        message_id: str,
        content: str,
    ) -> dict:
        """
        构建 TEXT_MESSAGE_CONTENT 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            message_id (str): Message ID。
            content (str): 文本内容。

        Returns:
            dict: AG-UI 事件。
        """
        event = self._base("TEXT_MESSAGE_CONTENT", run_id, thread_id)
        event["messageId"] = message_id
        event["delta"] = content
        return event

    def text_message_end(self, run_id: str, thread_id: str, message_id: str) -> dict:
        """
        构建 TEXT_MESSAGE_END 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            message_id (str): Message ID。

        Returns:
            dict: AG-UI 事件。
        """
        event = self._base("TEXT_MESSAGE_END", run_id, thread_id)
        event["messageId"] = message_id
        return event

    def step_finished(
        self,
        run_id: str,
        thread_id: str,
        step_index: int,
        state: LoopState,
    ) -> dict:
        """
        构建 STEP_FINISHED 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            step_index (int): 步骤序号。
            state (LoopState): 步骤结束状态。

        Returns:
            dict: AG-UI 事件。
        """
        event = self._base("STEP_FINISHED", run_id, thread_id)
        event["step"] = {"index": step_index, "state": state.value}
        return event

    def run_finished(self, run_id: str, thread_id: str, state: LoopState) -> dict:
        """
        构建 RUN_FINISHED 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            state (LoopState): 最终状态。

        Returns:
            dict: AG-UI 事件。
        """
        event = self._base("RUN_FINISHED", run_id, thread_id)
        event["state"] = state.value
        event["label"] = self._run_finished_label(state)
        return event

    def run_error(self, run_id: str, thread_id: str, message: str) -> dict:
        """
        构建 RUN_ERROR 事件。

        Args:
            run_id (str): Run ID。
            thread_id (str): Thread ID。
            message (str): 错误消息。

        Returns:
            dict: AG-UI 事件。
        """
        event = self._base("RUN_ERROR", run_id, thread_id)
        event["error"] = {"message": message}
        event["label"] = "无法继续完成"
        return event

    def new_message_id(self) -> str:
        """
        创建消息 ID。

        Returns:
            str: 消息 ID。
        """
        return uuid4().hex

    def new_tool_call_id(self) -> str:
        """
        创建 Tool Call ID。

        Returns:
            str: Tool Call ID。
        """
        return uuid4().hex

    def _base(self, event_type: str, run_id: str, thread_id: str) -> dict[str, Any]:
        """
        构建基础事件。

        Args:
            event_type (str): 事件类型。
            run_id (str): Run ID。
            thread_id (str): Thread ID。

        Returns:
            dict[str, Any]: 基础事件。
        """
        return {
            "type": event_type,
            "runId": run_id,
            "threadId": thread_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _planning_label(self, decision: ActionDecision) -> str:
        """
        获取下一步安排文案。

        Args:
            decision (ActionDecision): Action 决策。

        Returns:
            str: 展示文案。
        """
        if decision.action == LoopAction.CALL_SKILL:
            return self._skill_planning_label(self._tool_name(decision))
        if decision.action == LoopAction.CALL_AGENT:
            return self._worker_planning_label(self._tool_name(decision))
        if decision.action == LoopAction.ASK_USER:
            return "我需要先确认缺少的信息，再继续处理。"
        return "我会根据当前信息直接整理回答。"

    def _tool_name(self, decision: ActionDecision) -> str:
        """
        获取工具名称。

        Args:
            decision (ActionDecision): Action 决策。

        Returns:
            str: 工具名称。
        """
        if decision.action == LoopAction.CALL_SKILL:
            raw_name = str(
                decision.action_detail.get("skill_id")
                or decision.action_detail.get("name")
                or "unknown_skill"
            )
            return "content_extract" if raw_name == "content_extract_skill" else raw_name
        return str(
            decision.action_detail.get("worker_id")
            or decision.action_detail.get("name")
            or "unknown_worker"
        )

    def _tool_label(self, decision: ActionDecision) -> str:
        """
        获取工具展示文案。

        Args:
            decision (ActionDecision): Action 决策。

        Returns:
            str: 展示文案。
        """
        if decision.action == LoopAction.CALL_SKILL:
            return self._skill_tool_label(self._tool_name(decision))
        return self._worker_tool_label(self._tool_name(decision))

    def _skill_planning_label(self, skill_id: str) -> str:
        """
        获取 Skill 下一步安排文案。
        """
        labels = {
            "content_extract": "我会先整理你提供的文本，再提取出关键内容。",
            "amap_geocode": "我会先解析地址，确认后续查询需要的位置编码。",
            "amap_weather": "我会查询对应区域的天气，再整理成可读结果。",
            "amap_route_driving": "我会查询起终点之间的驾车路线。",
            "amap_route_weather_plan": "我会把地址解析、路线查询和天气查询串起来处理。",
            "travel_briefing_formatter": "我会把路线和天气结果整理成出行建议。",
        }
        return labels.get(skill_id, "我会调用合适的能力处理这一步。")

    def _skill_tool_label(self, skill_id: str) -> str:
        """
        获取 Skill 执行中展示文案。
        """
        labels = {
            "content_extract": "正在整理文本",
            "amap_geocode": "正在解析地址",
            "amap_weather": "正在查询天气",
            "amap_route_driving": "正在查询路线",
            "amap_route_weather_plan": "正在组合路线和天气",
            "travel_briefing_formatter": "正在生成出行建议",
        }
        return labels.get(skill_id, "正在调用能力")

    def _worker_planning_label(self, worker_id: str) -> str:
        """
        获取 Worker 下一步安排文案。
        """
        labels = {
            "amap_worker": "我会把地图、路线或天气相关部分交给高德 Worker 处理。",
        }
        return labels.get(worker_id, "我会调用合适的 Worker 处理这一步。")

    def _worker_tool_label(self, worker_id: str) -> str:
        """
        获取 Worker 执行中展示文案。
        """
        labels = {
            "amap_worker": "正在调用高德 Worker",
        }
        return labels.get(worker_id, "正在调用 Worker")

    def _summarize_args(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        脱敏参数摘要。

        Args:
            args (dict[str, Any]): 原始参数。

        Returns:
            dict[str, Any]: 参数摘要。
        """
        return {
            key: self._clip(str(value))
            for key, value in args.items()
            if key != "session_context"
        }

    def _feedback_delta(
        self,
        decision: ActionDecision,
        feedback: HarnessFeedback | None,
    ) -> dict[str, str]:
        """
        获取 Harness 可见状态变化。

        Args:
            decision (ActionDecision): Action 决策。
            feedback (HarnessFeedback | None): Harness 反馈。

        Returns:
            dict[str, str]: 状态变化。
        """
        if not feedback:
            return {"phase": "answering", "label": "正在生成最终回答"}
        if feedback.state == LoopState.MISSING_PARAMS:
            return {"phase": "need_more_info", "label": "还需要补充信息"}
        if feedback.state == LoopState.FAILED:
            return {"phase": "failed", "label": "这一步执行失败，正在整理原因"}
        if decision.action == LoopAction.CALL_SKILL:
            return {"phase": "tool_result_ready", "label": "能力调用已完成，正在组织回答"}
        return {"phase": "tool_result_ready", "label": "Worker 结果已返回，正在组织回答"}

    def _run_finished_label(self, state: LoopState) -> str:
        """
        获取 Run 结束展示文案。

        Args:
            state (LoopState): 最终状态。

        Returns:
            str: 展示文案。
        """
        if state == LoopState.COMPLETED:
            return "已完成"
        if state in {LoopState.MISSING_PARAMS, LoopState.AWAITING_USER}:
            return "需要补充信息"
        if state == LoopState.FAILED:
            return "无法继续完成"
        return "已结束"

    def _clip(self, text: str, limit: int = 160) -> str:
        """
        截断展示文本。

        Args:
            text (str): 原始文本。
            limit (int): 最大长度。

        Returns:
            str: 截断文本。
        """
        return text if len(text) <= limit else f"{text[:limit]}..."
