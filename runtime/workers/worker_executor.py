from typing import Any
from uuid import uuid4

from exception.error_code import BizErrorCode
from runtime.ag_ui.adapter import AGUIEventAdapter
from runtime.context.assembler import RuntimeContext
from runtime.models import ActionDecision, ActionResult, RuntimeRequest, RuntimeResult
from runtime.workers.worker_registry import WorkerRegistry


class WorkerExecutor:
    """
    Worker Agent 执行器。

    Attributes:
        worker_registry (WorkerRegistry): Worker 注册表。
    """

    def __init__(self, worker_registry: WorkerRegistry | None = None) -> None:
        """
        初始化 WorkerExecutor。

        Args:
            worker_registry (WorkerRegistry | None): Worker 注册表。
        """
        self.worker_registry = worker_registry or WorkerRegistry()

    async def execute(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
        agui_adapter: AGUIEventAdapter | None = None,
        parent_run_id: str | None = None,
        parent_session_id: str | None = None,
    ) -> ActionResult:
        """
        调用 Worker Agent，并将结果转换为主 Agent 的 ActionResult。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): call_agent 决策。
            agui_adapter (AGUIEventAdapter | None): 父 AG-UI 适配器。
            parent_run_id (str | None): 父 Run ID。
            parent_session_id (str | None): 父 Session ID。

        Returns:
            ActionResult: Worker 调用结果。
        """
        if context.agent_definition.kind != "main":
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception("Worker 不允许继续调用 Worker")
        worker_id = self._worker_id(decision)
        workers = self.worker_registry.load_workers()
        if worker_id not in workers:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(f"未知 Worker: {worker_id}")
        task_package = await self._build_task_package(context, decision, worker_id)
        worker_result = await self._run_worker(
            context,
            worker_id,
            task_package,
            agui_adapter,
            parent_run_id,
            parent_session_id,
        )
        return self._to_action_result(worker_id, task_package, worker_result)

    def _worker_id(self, decision: ActionDecision) -> str:
        """
        解析 Worker ID。

        Args:
            decision (ActionDecision): call_agent 决策。

        Returns:
            str: Worker ID。
        """
        worker_id = str(
            decision.action_detail.get("worker_id")
            or decision.action_detail.get("name")
            or ""
        ).strip()
        if not worker_id:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception("call_agent 缺少 worker_id")
        return worker_id

    async def _build_task_package(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
        worker_id: str,
    ) -> dict[str, Any]:
        """
        构建 Runtime 补全后的 Worker Task Package。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): call_agent 决策。
            worker_id (str): Worker ID。

        Returns:
            dict[str, Any]: Worker Task Package。
        """
        detail = decision.action_detail
        previous_result = (
            context.previous_action_result.to_dict()
            if context.previous_action_result
            else None
        )
        return {
            "worker_id": worker_id,
            "task": str(detail.get("task") or "").strip(),
            "handoff_context": str(detail.get("handoff_context") or "").strip(),
            "handoff": detail.get("handoff") if isinstance(detail.get("handoff"), dict) else {},
            "context_package": {
                "event_id": context.request.metadata.get("event_id", ""),
                "user_message": context.request.message,
                "conversation_summary": context.session_context.get("conversation_summary", ""),
                "event_history": context.action_history,
                "parent_session_context": self._parent_session_context(context),
                "recent_turns": context.session_context.get("recent_turns", []),
                "retrieved_context": [],
                "long_term_memory": [],
                "memory_palace_refs": [],
                "previous_worker_result": previous_result,
            },
            "output_contract": {
                "format": "structured_result",
                "final_answer_owner": "main_agent",
            },
        }

    async def _run_worker(
        self,
        context: RuntimeContext,
        worker_id: str,
        task_package: dict[str, Any],
        agui_adapter: AGUIEventAdapter | None = None,
        parent_run_id: str | None = None,
        parent_session_id: str | None = None,
    ) -> RuntimeResult:
        """
        启动 Worker Runtime。

        Args:
            context (RuntimeContext): Runtime 上下文。
            worker_id (str): Worker ID。
            task_package (dict[str, Any]): Worker Task Package。
            agui_adapter (AGUIEventAdapter | None): 父 AG-UI 适配器。
            parent_run_id (str | None): 父 Run ID。
            parent_session_id (str | None): 父 Session ID。

        Returns:
            RuntimeResult: Worker 运行结果。
        """
        from runtime.engine import RuntimeEngine

        message = self._worker_message(context, task_package)
        worker_metadata = dict(context.request.metadata)
        worker_metadata.update(
            {
                "runtime_role": "worker",
                "parent_agent_id": context.request.agent_id,
                "parent_request_id": context.request.request_id,
                "parent_session_id": context.session_state.session_id,
                "event_id": task_package.get("context_package", {}).get("event_id", ""),
                "worker_task_package": task_package,
            }
        )
        worker_request = RuntimeRequest(
            user_id=context.request.user_id,
            agent_id=worker_id,
            session_id=context.session_state.session_id,
            request_id=f"{context.request.request_id}:{worker_id}:{uuid4().hex[:8]}",
            message=str(message),
            metadata=worker_metadata,
        )
        worker_agui_adapter = self._worker_agui_adapter(
            parent_adapter=agui_adapter,
            worker_id=worker_id,
            parent_run_id=parent_run_id or "",
            parent_session_id=parent_session_id or context.session_state.session_id,
        )
        return await RuntimeEngine().run(worker_request, worker_agui_adapter)

    def _worker_agui_adapter(
        self,
        parent_adapter: AGUIEventAdapter | None,
        worker_id: str,
        parent_run_id: str,
        parent_session_id: str,
    ) -> AGUIEventAdapter | None:
        """
        构建 Worker 事件透传适配器。

        Args:
            parent_adapter (AGUIEventAdapter | None): 父 AG-UI 适配器。
            worker_id (str): Worker ID。
            parent_run_id (str): 父 Run ID。
            parent_session_id (str): 父 Session ID。

        Returns:
            AGUIEventAdapter | None: Worker AG-UI 适配器。
        """
        if not parent_adapter:
            return None

        async def emit(event: dict[str, Any]) -> None:
            mapped = self._map_worker_agui_event(
                event,
                worker_id,
                parent_run_id,
                parent_session_id,
            )
            if mapped:
                await parent_adapter.emit(mapped)

        return AGUIEventAdapter(emit)

    def _map_worker_agui_event(
        self,
        event: dict[str, Any],
        worker_id: str,
        parent_run_id: str,
        parent_session_id: str,
    ) -> dict[str, Any] | None:
        """
        过滤并包装 Worker AG-UI 事件。

        Args:
            event (dict[str, Any]): Worker 原始事件。
            worker_id (str): Worker ID。
            parent_run_id (str): 父 Run ID。
            parent_session_id (str): 父 Session ID。

        Returns:
            dict[str, Any] | None: 外层 UI 可展示事件。
        """
        event_type = str(event.get("type") or "")
        if event_type in {
            "RUN_STARTED",
            "STATE_SNAPSHOT",
            "STEP_STARTED",
            "STEP_FINISHED",
            "TEXT_MESSAGE_START",
            "TEXT_MESSAGE_CONTENT",
            "TEXT_MESSAGE_END",
        }:
            return None
        mapped = dict(event)
        mapped["threadId"] = parent_session_id
        mapped["source"] = "worker"
        mapped["sourceAgentId"] = worker_id
        mapped["parentRunId"] = parent_run_id
        mapped["parentToolCallId"] = f"{parent_run_id}:{worker_id}"
        mapped["depth"] = 1
        if event_type == "RUN_FINISHED":
            state = str(mapped.get("state") or "")
            if state != "completed":
                return None
            mapped["label"] = "Worker 领域结果已返回"
        if event_type == "RUN_ERROR":
            mapped["label"] = "Worker 执行失败"
        return mapped

    def _parent_session_context(self, context: RuntimeContext) -> dict[str, Any]:
        """
        构建给 Worker 的父会话上下文摘要。

        Args:
            context (RuntimeContext): Runtime 上下文。

        Returns:
            dict[str, Any]: 父会话上下文。
        """
        return {
            "pending_action": context.session_context.get("pending_action") or {},
            "missing_params": context.session_context.get("missing_params") or [],
            "conversation_summary": context.session_context.get("conversation_summary") or "",
        }

    def _worker_message(
        self,
        context: RuntimeContext,
        task_package: dict[str, Any],
    ) -> str:
        """
        构建 Worker 可直接理解的自然语言请求。

        Args:
            context (RuntimeContext): Runtime 上下文。
            task_package (dict[str, Any]): Worker Task Package。

        Returns:
            str: Worker 请求文本。
        """
        context_package = task_package.get("context_package") or {}
        parent_context = context_package.get("parent_session_context") or {}
        return (
            f"任务标题：{task_package.get('task') or ''}\n"
            f"任务交接：{task_package.get('handoff_context') or ''}\n"
            f"当前用户补充：{context.request.message}\n"
            f"父会话摘要：{parent_context.get('conversation_summary') or ''}\n"
            f"父会话待继续动作：{parent_context.get('pending_action') or {}}\n"
            f"父会话缺失信息：{parent_context.get('missing_params') or []}\n"
            "请结合以上信息完成 Worker 领域内任务。"
        ).strip()

    def _to_action_result(
        self,
        worker_id: str,
        task_package: dict[str, Any],
        worker_result: RuntimeResult,
    ) -> ActionResult:
        """
        转换 Worker Runtime 结果。

        Args:
            worker_id (str): Worker ID。
            task_package (dict[str, Any]): Worker Task Package。
            worker_result (RuntimeResult): Worker 运行结果。

        Returns:
            ActionResult: 主 Agent 可消费结果。
        """
        data = {
            "worker_id": worker_id,
            "worker_run_id": worker_result.run_id,
            "worker_session_id": worker_result.session_id,
            "worker_state": worker_result.state.value,
            "worker_answer": worker_result.answer,
            "worker_question": worker_result.question,
            "worker_result_data": worker_result.data,
            "worker_result_summary": worker_result.summary,
            "task_package": task_package,
        }
        if worker_result.question:
            return ActionResult(
                status="missing_params",
                data=data,
                summary="Worker 需要补充信息",
                question=worker_result.question,
                missing_params=["worker_required_information"],
            )
        if worker_result.state.value == "completed" and (
            worker_result.answer or worker_result.data
        ):
            return ActionResult(
                status="success",
                data=data,
                summary=worker_result.summary or "Worker 已返回处理结果",
            )
        worker_failure_reason = (
            worker_result.summary
            or worker_result.answer
            or "Worker 未返回答案或追问"
        )
        return ActionResult(
            status="failed",
            data=data,
            summary=worker_result.summary or "Worker 未能完成任务",
            error=worker_failure_reason,
        )
