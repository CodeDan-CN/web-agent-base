from dataclasses import dataclass
from typing import Any

from runtime.agents.loader import AgentDefinition
from runtime.models import ActionResult, RuntimeRequest
from schema.db.session_state import SessionState


@dataclass
class RuntimeContext:
    """
    Runtime 上下文。

    Attributes:
        request (RuntimeRequest): Runtime 请求。
        agent_definition (AgentDefinition): Agent 定义。
        session_state (SessionState): 会话状态。
        previous_action_result (ActionResult | None): 上一次动作结果。
        harness_feedback (dict[str, Any] | None): Harness 反馈。
        session_context (dict[str, Any]): mock executor 会话上下文。
    """

    request: RuntimeRequest
    agent_definition: AgentDefinition
    session_state: SessionState
    previous_action_result: ActionResult | None
    harness_feedback: dict[str, Any] | None
    session_context: dict[str, Any]


class ContextAssembler:
    """
    Runtime 上下文组装器。
    """

    def assemble(
        self,
        request: RuntimeRequest,
        agent_definition: AgentDefinition,
        session_state: SessionState,
        previous_action_result: ActionResult | None,
        harness_feedback: dict[str, Any] | None,
    ) -> RuntimeContext:
        """
        组装 Runtime 上下文。

        Args:
            request (RuntimeRequest): Runtime 请求。
            agent_definition (AgentDefinition): Agent 定义。
            session_state (SessionState): 会话状态。
            previous_action_result (ActionResult | None): 上一次动作结果。
            harness_feedback (dict[str, Any] | None): Harness 反馈。

        Returns:
            RuntimeContext: Runtime 上下文。
        """
        session_context = {
            "session_id": session_state.session_id,
            "pending_action": session_state.pending_action or {},
            "missing_params": session_state.missing_params or [],
            "previous_action_result": (
                previous_action_result.to_dict() if previous_action_result else None
            ),
            "conversation_summary": session_state.conversation_summary or "",
        }
        return RuntimeContext(
            request=request,
            agent_definition=agent_definition,
            session_state=session_state,
            previous_action_result=previous_action_result,
            harness_feedback=harness_feedback,
            session_context=session_context,
        )
