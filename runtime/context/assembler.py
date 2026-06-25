from dataclasses import dataclass
from typing import Any

from runtime.agents.loader import AgentDefinition
from runtime.context.event_preloader import EventPromptContext
from runtime.context.prompt_safety import remove_event_identifiers
from runtime.models import ActionResult, RuntimeRequest
from runtime.workers.worker_registry import WorkerRegistry
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
        session_context (dict[str, Any]): 会话上下文。
        skill_catalog (list[dict[str, Any]]): 当前 Agent 可用 Skill 目录。
        worker_catalog (list[dict[str, Any]]): 当前可用 Worker 目录。
        action_history (list[dict[str, Any]]): 当前 run 已完成动作历史。
        event_prompt_context (EventPromptContext): Loop 前事件对话上下文。
    """

    request: RuntimeRequest
    agent_definition: AgentDefinition
    session_state: SessionState
    previous_action_result: ActionResult | None
    harness_feedback: dict[str, Any] | None
    session_context: dict[str, Any]
    skill_catalog: list[dict[str, Any]]
    worker_catalog: list[dict[str, Any]]
    action_history: list[dict[str, Any]]
    event_prompt_context: EventPromptContext


class ContextAssembler:
    """
    Runtime 上下文组装器。
    """

    def __init__(self, worker_registry: WorkerRegistry | None = None) -> None:
        """
        初始化 ContextAssembler。

        Args:
            worker_registry (WorkerRegistry | None): Worker 注册表。
        """
        self.worker_registry = worker_registry or WorkerRegistry()

    def assemble(
        self,
        request: RuntimeRequest,
        agent_definition: AgentDefinition,
        session_state: SessionState,
        previous_action_result: ActionResult | None,
        harness_feedback: dict[str, Any] | None,
        action_history: list[dict[str, Any]] | None = None,
        event_prompt_context: EventPromptContext | None = None,
    ) -> RuntimeContext:
        """
        组装 Runtime 上下文。

        Args:
            request (RuntimeRequest): Runtime 请求。
            agent_definition (AgentDefinition): Agent 定义。
            session_state (SessionState): 会话状态。
            previous_action_result (ActionResult | None): 上一次动作结果。
            harness_feedback (dict[str, Any] | None): Harness 反馈。
            action_history (list[dict[str, Any]] | None): 当前 run 已完成动作历史。
            event_prompt_context (EventPromptContext | None): 事件对话上下文。

        Returns:
            RuntimeContext: Runtime 上下文。
        """
        prompt_event_context = event_prompt_context or EventPromptContext()
        session_context = {
            "session_id": session_state.session_id,
            "pending_action": session_state.pending_action or {},
            "missing_params": session_state.missing_params or [],
            "previous_action_result": (
                remove_event_identifiers(previous_action_result.to_dict())
                if previous_action_result
                else None
            ),
            "action_history": remove_event_identifiers(action_history or []),
            "conversation_summary": session_state.conversation_summary or "",
            "event_context": prompt_event_context.to_prompt_dict(),
        }
        return RuntimeContext(
            request=request,
            agent_definition=agent_definition,
            session_state=session_state,
            previous_action_result=previous_action_result,
            harness_feedback=harness_feedback,
            session_context=session_context,
            skill_catalog=agent_definition.skill_registry.list_for_prompt(),
            worker_catalog=self._worker_catalog(agent_definition),
            action_history=action_history or [],
            event_prompt_context=prompt_event_context,
        )

    def _worker_catalog(self, agent_definition: AgentDefinition) -> list[dict[str, Any]]:
        """
        获取当前 Agent 可见 Worker 目录。

        Args:
            agent_definition (AgentDefinition): 当前 Agent 定义。

        Returns:
            list[dict[str, Any]]: Worker 目录。
        """
        if agent_definition.kind != "main":
            return []
        return self.worker_registry.list_for_prompt()
