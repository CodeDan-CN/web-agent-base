import logging

from runtime.hooks.events import LoopStepCompletedEvent, ToolCallCompletedEvent
from schema.db.agent_run_step import AgentRunStep
from schema.db.tool_call import ToolCall

logger = logging.getLogger(__name__)


class RuntimeHook:
    """
    轻量 Runtime Hook。
    """

    async def on_loop_step_completed(self, event: LoopStepCompletedEvent) -> None:
        """
        处理 Loop 步骤完成事件。

        Args:
            event (LoopStepCompletedEvent): Loop 步骤完成事件。
        """
        try:
            await AgentRunStep.create(
                id=event.step_id,
                run_id=event.run_id,
                session_id=event.session_id,
                step_index=event.step_index,
                state_before=event.state_before,
                action=event.action,
                action_detail=event.action_detail,
                execution_result=event.execution_result,
                harness_feedback=event.harness_feedback,
                state_after=event.state_after,
            )
        except Exception:
            logger.exception("LoopStepCompleted hook failed")

    async def on_tool_call_completed(self, event: ToolCallCompletedEvent) -> None:
        """
        处理工具调用完成事件。

        Args:
            event (ToolCallCompletedEvent): 工具调用完成事件。
        """
        try:
            await ToolCall.create(
                id=event.tool_call_id,
                run_id=event.run_id,
                session_id=event.session_id,
                action=event.action,
                tool_name=event.tool_name,
                input_payload=event.input_payload,
                output_payload=event.output_payload,
                status=event.status,
            )
        except Exception:
            logger.exception("ToolCallCompleted hook failed")
