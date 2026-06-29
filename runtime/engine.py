import asyncio
from typing import Any
from uuid import uuid4

from exception.error_code import BizErrorCode
from runtime.actions.executor import ActionExecutor
from runtime.ag_ui.adapter import AGUIEventAdapter
from runtime.agents.loader import AgentLoader
from runtime.context.assembler import ContextAssembler
from runtime.context.event_preloader import EventContextPreloader
from runtime.events.manager import EventManager
from runtime.failure_message import (
    build_exception_failure_message,
    exception_reason,
)
from runtime.harness.evaluator import LLMHarnessEvaluator
from runtime.hooks.events import (
    ConversationTurnCompletedEvent,
    EventSummaryRequestedEvent,
    LoopStepCompletedEvent,
    ToolCallCompletedEvent,
)
from runtime.hooks.runtime_hook import RuntimeHook
from runtime.loop.decider import LLMLoopDecider
from runtime.models import (
    ActionDecision,
    ActionResult,
    HarnessFeedback,
    RuntimeRequest,
    RuntimeResult,
)
from runtime.state.manager import StateManager
from runtime.state.types import LoopAction, LoopState
from schema.db.agent_run import AgentRun
from utils.config import get_settings
from utils.llm_client import LLMClient


class RuntimeEngine:
    """
    Agent Runtime 主编排器。

    Attributes:
        llm_client (LLMClient): 模型调用客户端。
        agent_loader (AgentLoader): Agent 加载器。
        context_assembler (ContextAssembler): 上下文组装器。
        loop_decider (LLMLoopDecider): Loop 决策器。
        action_executor (ActionExecutor): Action 执行器。
        harness (LLMHarnessEvaluator): Harness 评估器。
        state_manager (StateManager): 状态管理器。
        event_manager (EventManager): 事件管理器。
        runtime_hook (RuntimeHook): Runtime Hook。
        event_preloader (EventContextPreloader): Loop 前事件上下文预加载器。
        max_loop_steps (int): 最大 Loop 步数。
    """

    def __init__(self) -> None:
        """
        初始化 RuntimeEngine。
        """
        settings = get_settings()
        self.llm_client = LLMClient()
        self.agent_loader = AgentLoader()
        self.context_assembler = ContextAssembler()
        self.loop_decider = LLMLoopDecider(self.llm_client)
        self.action_executor = ActionExecutor(self.llm_client)
        self.harness = LLMHarnessEvaluator(self.llm_client)
        self.state_manager = StateManager()
        self.event_manager = EventManager()
        self.runtime_hook = RuntimeHook()
        self.event_preloader = EventContextPreloader(self.llm_client)
        self.max_loop_steps = settings.max_loop_steps

    async def run(
        self,
        request: RuntimeRequest,
        agui_adapter: AGUIEventAdapter | None = None,
    ) -> RuntimeResult:
        """
        运行一次 Agent 请求。

        Args:
            request (RuntimeRequest): Runtime 请求。
            agui_adapter (AGUIEventAdapter | None): AG-UI 事件适配器。

        Returns:
            RuntimeResult: Runtime 运行结果。
        """
        agent_definition = self.agent_loader.load_agent(request.agent_id)
        session_state = await self.state_manager.load_or_create_session(request)
        request.session_id = session_state.session_id
        explicit_event_id = bool(str(request.metadata.get("event_id") or "").strip())
        event = await self.event_manager.resolve_event(request)
        request.metadata["event_id"] = event.event_id
        current_state = self.state_manager.state_for_new_run(session_state)
        run = await self._create_agent_run(request, session_state.session_id, current_state)
        await self.event_manager.link_run(event, request, run.id)
        event_prompt_context = await self.event_preloader.preload(
            user_id=request.user_id,
            session_id=session_state.session_id,
            agent_id=request.agent_id,
            event_id=event.event_id,
            user_message=request.message,
            explicit_event_id=explicit_event_id,
            allow_related_lookup=agent_definition.kind == "main",
            exclude_run_id=run.id,
        )
        await self._emit_agui(
            agui_adapter,
            agui_adapter.run_started(run.id, session_state.session_id)
            if agui_adapter
            else None,
        )
        await self._emit_agui(
            agui_adapter,
            agui_adapter.state_snapshot(run.id, session_state.session_id, current_state)
            if agui_adapter
            else None,
        )
        previous_result: ActionResult | None = None
        harness_feedback: HarnessFeedback | None = None
        pending_action: ActionDecision | None = None
        missing_params: list[str] = []
        final_answer: str | None = None
        final_question: str | None = None
        final_data: Any = None
        final_summary = ""
        final_state = current_state
        action_history: list[dict] = []
        try:
            for step_index in range(1, self.max_loop_steps + 1):
                await self._emit_agui(
                    agui_adapter,
                    agui_adapter.step_started(run.id, session_state.session_id, step_index)
                    if agui_adapter
                    else None,
                )
                context = await self.context_assembler.assemble(
                    request=request,
                    agent_definition=agent_definition,
                    session_state=session_state,
                    previous_action_result=previous_result,
                    harness_feedback=(
                        harness_feedback.to_dict() if harness_feedback else None
                    ),
                    action_history=action_history,
                    event_prompt_context=event_prompt_context,
                )
                state_before = final_state
                decision = await self.loop_decider.decide(state_before, context)
                await self._emit_agui(
                    agui_adapter,
                    agui_adapter.planning_next(run.id, session_state.session_id, decision)
                    if agui_adapter
                    else None,
                )
                tool_call_id = (
                    agui_adapter.new_tool_call_id()
                    if agui_adapter
                    and decision.action in {LoopAction.CALL_SKILL, LoopAction.CALL_AGENT}
                    else uuid4().hex
                )
                await self._emit_tool_start_if_needed(
                    agui_adapter,
                    run.id,
                    session_state.session_id,
                    tool_call_id,
                    decision,
                )
                result = await self.action_executor.execute(
                    context,
                    decision,
                    agui_adapter,
                    run.id,
                    session_state.session_id,
                )
                await self._emit_tool_end_if_needed(
                    agui_adapter,
                    run.id,
                    session_state.session_id,
                    tool_call_id,
                    decision,
                    result,
                )
                feedback = await self._evaluate_if_needed(context, decision, result)
                if feedback:
                    await self._emit_agui(
                        agui_adapter,
                        agui_adapter.harness_delta(
                            run.id,
                            session_state.session_id,
                            decision,
                            feedback,
                        )
                        if agui_adapter
                        else None,
                    )
                next_state = self._resolve_next_state(
                    state_before,
                    decision,
                    feedback,
                )
                action_history.append(
                    self._build_action_history_item(
                        step_index,
                        state_before,
                        decision,
                        result,
                        feedback,
                        next_state,
                    )
                )
                await self._emit_text_if_needed(
                    agui_adapter,
                    run.id,
                    session_state.session_id,
                    decision,
                    result,
                )
                await self._emit_tool_call_if_needed(
                    run.id,
                    session_state.session_id,
                    tool_call_id,
                    decision,
                    context.session_context,
                    request.message,
                    result,
                )
                await self._emit_loop_step(
                    run.id,
                    session_state.session_id,
                    step_index,
                    state_before,
                    decision,
                    result,
                    feedback,
                    next_state,
                )
                await self._emit_agui(
                    agui_adapter,
                    agui_adapter.step_finished(
                        run.id,
                        session_state.session_id,
                        step_index,
                        next_state,
                    )
                    if agui_adapter
                    else None,
                )
                previous_result = result
                harness_feedback = feedback
                final_state = next_state
                if decision.action in {LoopAction.CALL_SKILL, LoopAction.CALL_AGENT}:
                    pending_action = decision
                if decision.action == LoopAction.ASK_USER and pending_action is None:
                    pending_action = decision
                missing_params = self.state_manager.missing_params_from_feedback(
                    feedback,
                    result,
                )
                if next_state == LoopState.FAILED:
                    pending_action = None
                    missing_params = []
                session_state.state = next_state.value
                session_state.missing_params = missing_params
                session_state.pending_action = None
                if pending_action:
                    session_state.pending_action = {
                        "action": pending_action.action.value,
                        "action_detail": pending_action.action_detail,
                        "reason": pending_action.reason,
                    }
                if next_state == LoopState.COMPLETED:
                    final_answer = result.answer
                    final_data = result.data
                    final_summary = result.summary
                    break
                if next_state == LoopState.AWAITING_USER:
                    final_question = result.question
                    break
                if next_state == LoopState.FAILED:
                    if state_before == LoopState.FAILED and decision.action == LoopAction.ANSWER_USER:
                        final_answer = result.answer
                        final_data = result.data
                        final_summary = result.summary
                        break
                    continue
            else:
                raise BizErrorCode.STATE_ERROR.exception("超过最大 Loop 步数")
            await self.state_manager.flush_boundary_state(
                session_state=session_state,
                state=final_state,
                loop_count=step_index,
                pending_action=pending_action,
                missing_params=missing_params,
                result=previous_result,
                user_message=request.message,
            )
            await self._finish_agent_run(run, final_state, final_answer, None)
            self._request_conversation_turn_completed(
                run.id,
                event.event_id,
                request,
                session_state.session_id,
                final_state,
                final_answer,
                final_question,
                previous_result,
            )
            if request.agent_id == event.root_agent_id:
                event = await self.event_manager.update_status(event, final_state)
                self._request_event_summary_if_needed(
                    event.event_id,
                    request,
                    final_state,
                )
            await self._emit_agui(
                agui_adapter,
                agui_adapter.run_finished(run.id, session_state.session_id, final_state)
                if agui_adapter
                else None,
            )
            execution_report = self._build_execution_report(
                request=request,
                final_state=final_state,
                final_answer=final_answer,
                final_question=final_question,
                final_summary=final_summary,
                final_data=final_data,
                previous_result=previous_result,
                harness_feedback=harness_feedback,
                action_history=action_history,
            )
            return RuntimeResult(
                request_id=request.request_id,
                session_id=session_state.session_id,
                run_id=run.id,
                state=final_state,
                answer=final_answer,
                question=final_question,
                data=final_data or {},
                summary=final_summary,
                execution_report=execution_report,
            )
        except Exception as exc:
            failure_answer = build_exception_failure_message(exc)
            failure_reason = exception_reason(exc)
            await self._finish_agent_run(
                run,
                LoopState.FAILED,
                failure_answer,
                failure_reason,
            )
            if request.agent_id == event.root_agent_id:
                event = await self.event_manager.update_status(event, LoopState.FAILED)
                self._request_event_summary_if_needed(
                    event.event_id,
                    request,
                    LoopState.FAILED,
                )
            self._request_conversation_turn_completed(
                run.id,
                event.event_id,
                request,
                session_state.session_id,
                LoopState.FAILED,
                failure_answer,
                None,
                None,
            )
            await self._emit_message(
                agui_adapter,
                run.id,
                session_state.session_id,
                failure_answer,
            )
            await self._emit_agui(
                agui_adapter,
                agui_adapter.run_error(
                    run.id,
                    session_state.session_id,
                    failure_reason,
                )
                if agui_adapter
                else None,
            )
            return RuntimeResult(
                request_id=request.request_id,
                session_id=session_state.session_id,
                run_id=run.id,
                state=LoopState.FAILED,
                answer=failure_answer,
                question=None,
                data={},
                summary=failure_reason,
                execution_report=self._build_exception_execution_report(
                    request=request,
                    action_history=action_history,
                    error_reason=failure_reason,
                ),
            )

    def _request_conversation_turn_completed(
        self,
        run_id: str,
        event_id: str,
        request: RuntimeRequest,
        session_id: str,
        final_state: LoopState,
        final_answer: str | None,
        final_question: str | None,
        result: ActionResult | None,
    ) -> None:
        """
        触发对话轮次完成 Hook。

        Args:
            run_id (str): AgentRun ID。
            event_id (str): 事件 ID。
            request (RuntimeRequest): Runtime 请求。
            session_id (str): 会话 ID。
            final_state (LoopState): 最终状态。
            final_answer (str | None): 最终回答。
            final_question (str | None): 最终追问。
            result (ActionResult | None): 最后一次 Action 结果。
        """
        assistant_message = final_answer or final_question or ""
        if not assistant_message and result:
            assistant_message = result.summary or result.error or ""
        if not assistant_message:
            return
        asyncio.create_task(
            self.runtime_hook.on_conversation_turn_completed(
                ConversationTurnCompletedEvent(
                    run_id=run_id,
                    session_id=session_id,
                    user_id=request.user_id,
                    agent_id=request.agent_id,
                    event_id=event_id,
                    user_message=request.message,
                    assistant_message=assistant_message,
                    final_state=final_state.value,
                )
            )
        )

    def _request_event_summary_if_needed(
        self,
        event_id: str,
        request: RuntimeRequest,
        final_state: LoopState,
    ) -> None:
        """
        必要时触发事件摘要 Hook。

        Args:
            event_id (str): 事件 ID。
            request (RuntimeRequest): Runtime 请求。
            final_state (LoopState): 最终状态。
        """
        if final_state not in {LoopState.COMPLETED, LoopState.FAILED}:
            return
        asyncio.create_task(
            self.runtime_hook.on_event_summary_requested(
                EventSummaryRequestedEvent(
                    event_id=event_id,
                    user_id=request.user_id,
                    session_id=request.session_id or "",
                    trigger_agent_id=request.agent_id,
                    final_state=final_state.value,
                )
            )
        )

    async def _create_agent_run(
        self,
        request: RuntimeRequest,
        session_id: str,
        initial_state: LoopState,
    ) -> AgentRun:
        """
        创建 AgentRun。

        Args:
            request (RuntimeRequest): Runtime 请求。
            session_id (str): 会话 ID。
            initial_state (LoopState): 初始状态。

        Returns:
            AgentRun: 运行记录。
        """
        return await AgentRun.create(
            id=uuid4().hex,
            request_id=request.request_id,
            session_id=session_id,
            user_id=request.user_id,
            agent_id=request.agent_id,
            user_message=request.message,
            initial_state=initial_state.value,
        )

    async def _finish_agent_run(
        self,
        run: AgentRun,
        final_state: LoopState,
        final_answer: str | None,
        error_message: str | None,
    ) -> None:
        """
        完成 AgentRun。

        Args:
            run (AgentRun): 运行记录。
            final_state (LoopState): 最终状态。
            final_answer (str | None): 最终回答。
            error_message (str | None): 错误信息。
        """
        run.final_state = final_state.value
        run.final_answer = final_answer
        run.error_message = error_message
        await run.save()

    async def _evaluate_if_needed(
        self,
        context,
        decision: ActionDecision,
        result: ActionResult,
    ) -> HarnessFeedback | None:
        """
        必要时调用 Harness。

        Args:
            context: Runtime 上下文。
            decision (ActionDecision): Action 决策。
            result (ActionResult): Action 结果。

        Returns:
            HarnessFeedback | None: Harness 反馈。
        """
        if decision.action in {LoopAction.CALL_SKILL, LoopAction.CALL_AGENT}:
            return await self.harness.evaluate(context, decision, result)
        return None

    def _resolve_next_state(
        self,
        current_state: LoopState,
        decision: ActionDecision,
        feedback: HarnessFeedback | None,
    ) -> LoopState:
        """
        计算下一状态。

        Args:
            current_state (LoopState): 当前状态。
            decision (ActionDecision): Action 决策。
            feedback (HarnessFeedback | None): Harness 反馈。

        Returns:
            LoopState: 下一状态。
        """
        if feedback:
            return feedback.state
        return self.state_manager.next_state_for_direct_action(
            current_state,
            decision.action,
        )

    def _build_action_history_item(
        self,
        step_index: int,
        state_before: LoopState,
        decision: ActionDecision,
        result: ActionResult,
        feedback: HarnessFeedback | None,
        state_after: LoopState,
    ) -> dict:
        """
        构建当前 run 内给下一步 LoopDecider 使用的动作历史。

        Args:
            step_index (int): 步骤序号。
            state_before (LoopState): 执行前状态。
            decision (ActionDecision): Action 决策。
            result (ActionResult): Action 结果。
            feedback (HarnessFeedback | None): Harness 反馈。
            state_after (LoopState): 执行后状态。

        Returns:
            dict: 动作历史项。
        """
        return {
            "step_index": step_index,
            "state_before": state_before.value,
            "action": decision.action.value,
            "action_detail": decision.action_detail,
            "execution_result": result.to_dict(),
            "harness_feedback": feedback.to_dict() if feedback else None,
            "state_after": state_after.value,
        }

    async def _emit_loop_step(
        self,
        run_id: str,
        session_id: str,
        step_index: int,
        state_before: LoopState,
        decision: ActionDecision,
        result: ActionResult,
        feedback: HarnessFeedback | None,
        state_after: LoopState,
    ) -> None:
        """
        触发 LoopStepCompleted 事件。

        Args:
            run_id (str): 运行 ID。
            session_id (str): 会话 ID。
            step_index (int): 步骤序号。
            state_before (LoopState): 执行前状态。
            decision (ActionDecision): Action 决策。
            result (ActionResult): Action 结果。
            feedback (HarnessFeedback | None): Harness 反馈。
            state_after (LoopState): 执行后状态。
        """
        await self.runtime_hook.on_loop_step_completed(
            LoopStepCompletedEvent(
                step_id=uuid4().hex,
                run_id=run_id,
                session_id=session_id,
                step_index=step_index,
                state_before=state_before.value,
                action=decision.action.value,
                action_detail=decision.action_detail,
                execution_result=result.to_dict(),
                harness_feedback=feedback.to_dict() if feedback else None,
                state_after=state_after.value,
            )
        )

    async def _emit_agui(
        self,
        agui_adapter: AGUIEventAdapter | None,
        event: dict | None,
    ) -> None:
        """
        输出 AG-UI 事件。

        Args:
            agui_adapter (AGUIEventAdapter | None): AG-UI 适配器。
            event (dict | None): AG-UI 事件。
        """
        if agui_adapter and event:
            await agui_adapter.emit(event)

    async def _emit_tool_start_if_needed(
        self,
        agui_adapter: AGUIEventAdapter | None,
        run_id: str,
        session_id: str,
        tool_call_id: str,
        decision: ActionDecision,
    ) -> None:
        """
        必要时输出 AG-UI 工具开始事件。

        Args:
            agui_adapter (AGUIEventAdapter | None): AG-UI 适配器。
            run_id (str): 运行 ID。
            session_id (str): 会话 ID。
            tool_call_id (str): Tool Call ID。
            decision (ActionDecision): Action 决策。
        """
        if not agui_adapter:
            return
        if decision.action not in {LoopAction.CALL_SKILL, LoopAction.CALL_AGENT}:
            return
        await agui_adapter.emit(
            agui_adapter.tool_call_start(run_id, session_id, tool_call_id, decision)
        )
        await agui_adapter.emit(
            agui_adapter.tool_call_args(run_id, session_id, tool_call_id, decision)
        )

    async def _emit_tool_end_if_needed(
        self,
        agui_adapter: AGUIEventAdapter | None,
        run_id: str,
        session_id: str,
        tool_call_id: str,
        decision: ActionDecision,
        result: ActionResult,
    ) -> None:
        """
        必要时输出 AG-UI 工具结束事件。

        Args:
            agui_adapter (AGUIEventAdapter | None): AG-UI 适配器。
            run_id (str): 运行 ID。
            session_id (str): 会话 ID。
            tool_call_id (str): Tool Call ID。
            decision (ActionDecision): Action 决策。
            result (ActionResult): Action 结果。
        """
        if not agui_adapter:
            return
        if decision.action not in {LoopAction.CALL_SKILL, LoopAction.CALL_AGENT}:
            return
        await agui_adapter.emit(
            agui_adapter.tool_call_end(run_id, session_id, tool_call_id, result)
        )

    async def _emit_text_if_needed(
        self,
        agui_adapter: AGUIEventAdapter | None,
        run_id: str,
        session_id: str,
        decision: ActionDecision,
        result: ActionResult,
    ) -> None:
        """
        必要时输出 AG-UI 文本消息事件。

        Args:
            agui_adapter (AGUIEventAdapter | None): AG-UI 适配器。
            run_id (str): 运行 ID。
            session_id (str): 会话 ID。
            decision (ActionDecision): Action 决策。
            result (ActionResult): Action 结果。
        """
        if not agui_adapter:
            return
        if decision.action != LoopAction.ASK_USER:
            return
        content = result.question
        if not content:
            return
        await self._emit_message(agui_adapter, run_id, session_id, content)

    async def _emit_message(
        self,
        agui_adapter: AGUIEventAdapter | None,
        run_id: str,
        session_id: str,
        content: str | None,
    ) -> None:
        """
        输出一条完整的 AG-UI assistant 文本消息。

        Args:
            agui_adapter (AGUIEventAdapter | None): AG-UI 适配器。
            run_id (str): 运行 ID。
            session_id (str): 会话 ID。
            content (str | None): 消息内容。
        """
        if not agui_adapter:
            return
        normalized = str(content or "").strip()
        if not normalized:
            return
        message_id = agui_adapter.new_message_id()
        await agui_adapter.emit(
            agui_adapter.text_message_start(run_id, session_id, message_id)
        )
        await agui_adapter.emit(
            agui_adapter.text_message_content(run_id, session_id, message_id, normalized)
        )
        await agui_adapter.emit(agui_adapter.text_message_end(run_id, session_id, message_id))

    async def _emit_tool_call_if_needed(
        self,
        run_id: str,
        session_id: str,
        tool_call_id: str,
        decision: ActionDecision,
        session_context: dict,
        user_message: str,
        result: ActionResult,
    ) -> None:
        """
        必要时触发 ToolCallCompleted 事件。

        Args:
            run_id (str): 运行 ID。
            session_id (str): 会话 ID。
            decision (ActionDecision): Action 决策。
            session_context (dict): 会话上下文。
            user_message (str): 用户消息。
            result (ActionResult): Action 结果。
        """
        if decision.action not in {LoopAction.CALL_SKILL, LoopAction.CALL_AGENT}:
            return
        if decision.action == LoopAction.CALL_SKILL:
            action_input = decision.action_detail.get("input") or {}
            input_payload = dict(action_input) if isinstance(action_input, dict) else {}
        else:
            input_payload = dict(decision.action_detail)
        input_payload["user_message"] = user_message
        input_payload["session_context"] = session_context
        tool_name = self._tool_name(decision)
        await self.runtime_hook.on_tool_call_completed(
            ToolCallCompletedEvent(
                tool_call_id=tool_call_id,
                run_id=run_id,
                session_id=session_id,
                action=decision.action.value,
                tool_name=tool_name,
                input_payload=input_payload,
                output_payload=result.to_dict(),
                status=result.status,
            )
        )

    def _tool_name(self, decision: ActionDecision) -> str:
        """
        获取工具或 worker 名称。

        Args:
            decision (ActionDecision): Action 决策。

        Returns:
            str: 工具或 worker 名称。
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

    def _build_execution_report(
        self,
        request: RuntimeRequest,
        final_state: LoopState,
        final_answer: str | None,
        final_question: str | None,
        final_summary: str,
        final_data: Any,
        previous_result: ActionResult | None,
        harness_feedback: HarnessFeedback | None,
        action_history: list[dict[str, Any]],
    ) -> str | None:
        """
        为 worker runtime 构建整轮执行汇总文本。

        Args:
            request (RuntimeRequest): Runtime 请求。
            final_state (LoopState): 最终状态。
            final_answer (str | None): 最终回答。
            final_question (str | None): 最终追问。
            final_summary (str): 最终摘要。
            final_data (Any): 最终数据。
            previous_result (ActionResult | None): 最后一次动作结果。
            harness_feedback (HarnessFeedback | None): 最后一次 Harness 反馈。
            action_history (list[dict[str, Any]]): 当前 run 动作历史。

        Returns:
            str | None: 汇总文本。
        """
        if str(request.metadata.get("runtime_role") or "") != "worker":
            return None
        task_package = request.metadata.get("worker_task_package")
        if not isinstance(task_package, dict):
            return None
        lines = [
            "[Worker Task]",
            f"worker_id: {request.agent_id}",
            f"task: {str(task_package.get('task') or '').strip() or '未提供'}",
            f"handoff_context: {str(task_package.get('handoff_context') or '').strip() or '未提供'}",
            "",
            "[Loop Summary]",
        ]
        if action_history:
            for item in action_history:
                lines.append(self._format_action_history_line(item))
        else:
            lines.append("no_steps | 当前 worker 未记录可用步骤")
        final_status = (
            previous_result.status
            if previous_result and previous_result.status
            else final_state.value
        )
        final_missing_params = (
            previous_result.missing_params
            if previous_result and previous_result.missing_params
            else []
        )
        final_error = (
            previous_result.error
            if previous_result and previous_result.error
            else "none"
        )
        answer_or_question = final_question or final_answer or "none"
        lines.extend(
            [
                "",
                "[Final Result]",
                f"final_state: {final_state.value}",
                f"final_status: {final_status}",
                f"final_summary: {final_summary or (previous_result.summary if previous_result else '') or 'none'}",
                f"final_missing_params: {final_missing_params}",
                f"final_error: {final_error}",
                f"final_question_or_answer: {self._clip_text(str(answer_or_question), 240)}",
            ]
        )
        if harness_feedback:
            lines.extend(
                [
                    "",
                    "[Final Harness]",
                    f"state: {harness_feedback.state.value}",
                    f"status: {harness_feedback.status or 'none'}",
                    f"summary: {harness_feedback.summary or 'none'}",
                    f"reason: {harness_feedback.reason or 'none'}",
                    f"suggested_question: {harness_feedback.suggested_question or 'none'}",
                ]
            )
        if final_data not in (None, {}, []):
            lines.extend(
                [
                    "",
                    "[Latest Result Snapshot]",
                    self._clip_text(str(final_data), 800),
                ]
            )
        return "\n".join(lines)

    def _build_exception_execution_report(
        self,
        request: RuntimeRequest,
        action_history: list[dict[str, Any]],
        error_reason: str,
    ) -> str | None:
        """
        为 worker 异常终止场景构建执行汇总文本。

        Args:
            request (RuntimeRequest): Runtime 请求。
            action_history (list[dict[str, Any]]): 当前 run 动作历史。
            error_reason (str): 异常原因。

        Returns:
            str | None: 汇总文本。
        """
        if str(request.metadata.get("runtime_role") or "") != "worker":
            return None
        lines = [
            "[Worker Task]",
            f"worker_id: {request.agent_id}",
            f"task: {str((request.metadata.get('worker_task_package') or {}).get('task') or '').strip() or '未提供'}",
            "",
            "[Loop Summary]",
        ]
        if action_history:
            for item in action_history:
                lines.append(self._format_action_history_line(item))
        else:
            lines.append("no_steps | 当前 worker 在异常前没有完成可记录步骤")
        lines.extend(
            [
                "",
                "[Final Result]",
                "final_state: failed",
                "final_status: failed",
                "final_summary: worker 运行异常终止",
                "final_missing_params: []",
                f"final_error: {error_reason or '未知异常'}",
                "final_question_or_answer: none",
            ]
        )
        return "\n".join(lines)

    def _format_action_history_line(self, item: dict[str, Any]) -> str:
        """
        将动作历史项格式化为稳定文本行。

        Args:
            item (dict[str, Any]): 动作历史项。

        Returns:
            str: 文本行。
        """
        action = str(item.get("action") or "unknown")
        action_detail = item.get("action_detail") or {}
        execution_result = item.get("execution_result") or {}
        state_after = str(item.get("state_after") or "unknown")
        target = self._action_target_name(action, action_detail)
        summary = (
            str(execution_result.get("summary") or execution_result.get("question") or "")
            or "无摘要"
        )
        status = str(execution_result.get("status") or "unknown")
        error = str(execution_result.get("error") or "").strip() or "none"
        missing_params = execution_result.get("missing_params") or []
        return (
            f"step_{item.get('step_index')} | action={action} | target={target} "
            f"| status={status} | summary={self._clip_text(summary, 160)} "
            f"| state_after={state_after} | missing_params={missing_params} | error={self._clip_text(error, 120)}"
        )

    def _action_target_name(self, action: str, action_detail: dict[str, Any]) -> str:
        """
        获取动作目标名称。

        Args:
            action (str): 动作名称。
            action_detail (dict[str, Any]): 动作详情。

        Returns:
            str: 目标名称。
        """
        if action == LoopAction.CALL_SKILL.value:
            return str(
                action_detail.get("skill_id")
                or action_detail.get("name")
                or "unknown_skill"
            )
        if action == LoopAction.CALL_AGENT.value:
            return str(
                action_detail.get("worker_id")
                or action_detail.get("name")
                or "unknown_worker"
            )
        return action

    def _clip_text(self, text: str, limit: int) -> str:
        """
        截断展示文本。

        Args:
            text (str): 原始文本。
            limit (int): 最大长度。

        Returns:
            str: 截断结果。
        """
        normalized = " ".join(text.strip().split())
        if not normalized:
            return "none"
        return normalized if len(normalized) <= limit else f"{normalized[:limit]}..."
