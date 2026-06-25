import logging
from uuid import uuid4

from runtime.hooks.events import (
    EventSummaryRequestedEvent,
    LoopStepCompletedEvent,
    ToolCallCompletedEvent,
)
from schema.db.agent_event import AgentEventContext, AgentEventRun
from schema.db.agent_run import AgentRun
from schema.db.agent_run_step import AgentRunStep
from schema.db.tool_call import ToolCall
from utils.config import get_settings
from utils.llm_client import LLMClient

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

    async def on_event_summary_requested(self, event: EventSummaryRequestedEvent) -> None:
        """
        处理事件摘要请求。

        Args:
            event (EventSummaryRequestedEvent): 事件摘要请求。
        """
        try:
            agent_ids = await self._agent_ids_for_event(event.event_id)
            for agent_id in agent_ids:
                await self._update_agent_event_summary(event, agent_id)
        except Exception:
            logger.exception("EventSummaryRequested hook failed")

    async def _agent_ids_for_event(self, event_id: str) -> list[str]:
        """
        查询事件下出现过的 Agent ID。

        Args:
            event_id (str): 事件 ID。

        Returns:
            list[str]: Agent ID 列表。
        """
        rows = await AgentEventRun.filter(event_id=event_id).values("agent_id")
        agent_ids = sorted({str(row["agent_id"]) for row in rows})
        return agent_ids

    async def _update_agent_event_summary(
        self,
        event: EventSummaryRequestedEvent,
        agent_id: str,
    ) -> None:
        """
        更新单个 Agent 的事件摘要。

        Args:
            event (EventSummaryRequestedEvent): 事件摘要请求。
            agent_id (str): Agent ID。
        """
        source = await self._summary_source(event.event_id, agent_id)
        if not source:
            return
        settings = get_settings()
        turn_count = source.count("用户输入:")
        char_count = len(source)
        if (
            turn_count <= settings.event_summary_direct_max_turns
            and char_count <= settings.event_summary_direct_max_chars
        ):
            summary = source
            mode = "direct"
        else:
            summary = await self._llm_summary(
                source,
                settings.event_summary_target_chars,
            )
            mode = "llm"
        existing = await AgentEventContext.get_or_none(
            event_id=event.event_id,
            agent_id=agent_id,
        )
        if existing:
            existing.summary = summary
            existing.turn_count = turn_count
            existing.char_count = char_count
            existing.summarize_mode = mode
            existing.metadata = {
                "trigger_agent_id": event.trigger_agent_id,
                "final_state": event.final_state,
            }
            await existing.save()
            return
        await AgentEventContext.create(
            id=uuid4().hex,
            event_id=event.event_id,
            user_id=event.user_id,
            agent_id=agent_id,
            summary=summary,
            turn_count=turn_count,
            char_count=char_count,
            summarize_mode=mode,
            metadata={
                "trigger_agent_id": event.trigger_agent_id,
                "final_state": event.final_state,
            },
        )

    async def _summary_source(self, event_id: str, agent_id: str) -> str:
        """
        构造事件摘要源文本。

        Args:
            event_id (str): 事件 ID。
            agent_id (str): Agent ID。

        Returns:
            str: 摘要源文本。
        """
        links = await AgentEventRun.filter(
            event_id=event_id,
            agent_id=agent_id,
        ).order_by("created_at")
        parts: list[str] = []
        for link in links:
            run = await AgentRun.get_or_none(id=link.run_id)
            if not run:
                continue
            parts.append(f"用户输入: {run.user_message}")
            if run.final_answer:
                parts.append(f"最终回答: {run.final_answer}")
            if run.error_message:
                parts.append(f"错误: {run.error_message}")
            steps = await AgentRunStep.filter(run_id=run.id).order_by("step_index")
            for step in steps:
                parts.append(
                    f"步骤{step.step_index}: {step.state_before} -> "
                    f"{step.action} -> {step.state_after}"
                )
                result = step.execution_result or {}
                summary = result.get("summary")
                question = result.get("question")
                if summary:
                    parts.append(f"步骤摘要: {summary}")
                if question:
                    parts.append(f"追问: {question}")
            calls = await ToolCall.filter(run_id=run.id).order_by("created_at")
            for call in calls:
                output = call.output_payload or {}
                parts.append(
                    f"能力调用: {call.action}:{call.tool_name} "
                    f"状态={call.status} 摘要={output.get('summary', '')}"
                )
        return "\n".join(parts).strip()

    async def _llm_summary(self, source: str, target_chars: int) -> str:
        """
        使用模型生成事件摘要。

        Args:
            source (str): 摘要源文本。
            target_chars (int): 目标字符数。

        Returns:
            str: 摘要文本。
        """
        system_prompt = "你是事件摘要器，只输出摘要正文。"
        user_prompt = (
            f"请把以下事件过程总结为约 {target_chars} 个中文字符。"
            "保留用户目标、关键参数、已完成动作和最终结论。"
            "不要输出条目标题、Markdown 或内部实现术语。\n\n"
            f"{source}"
        )
        return await LLMClient().chat_text(system_prompt, user_prompt, max_tokens=600)
