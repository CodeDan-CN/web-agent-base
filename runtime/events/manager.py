from datetime import UTC, datetime
from uuid import uuid4

from runtime.models import RuntimeRequest
from runtime.state.types import LoopState
from schema.db.agent_event import AgentEvent, AgentEventRun


class EventManager:
    """
    Agent 事件管理器。
    """

    async def resolve_event(self, request: RuntimeRequest) -> AgentEvent:
        """
        获取或创建当前请求所属事件。

        Args:
            request (RuntimeRequest): Runtime 请求。

        Returns:
            AgentEvent: 当前事件。
        """
        event_id = str(request.metadata.get("event_id") or "").strip()
        if event_id:
            event = await AgentEvent.get_or_none(event_id=event_id)
            if event:
                return event
            return await self._create_event(request, event_id=event_id)
        if request.agent_id != "main":
            return await self._create_event(request)
        existing = await AgentEvent.filter(
            user_id=request.user_id,
            session_id=request.session_id or "",
            root_agent_id=request.agent_id,
            status__in=["open", "awaiting_user"],
        ).order_by("-created_at").first()
        if existing:
            return existing
        return await self._create_event(request)

    async def link_run(
        self,
        event: AgentEvent,
        request: RuntimeRequest,
        run_id: str,
    ) -> None:
        """
        关联事件和 run。

        Args:
            event (AgentEvent): 当前事件。
            request (RuntimeRequest): Runtime 请求。
            run_id (str): run ID。
        """
        existing = await AgentEventRun.get_or_none(run_id=run_id)
        if existing:
            return
        await AgentEventRun.create(
            id=uuid4().hex,
            event_id=event.event_id,
            run_id=run_id,
            user_id=request.user_id,
            agent_id=request.agent_id,
            session_id=request.session_id or "",
        )

    async def update_status(self, event: AgentEvent, state: LoopState) -> AgentEvent:
        """
        根据主 Agent 最终状态更新事件状态。

        Args:
            event (AgentEvent): 当前事件。
            state (LoopState): 最终 Loop 状态。

        Returns:
            AgentEvent: 更新后的事件。
        """
        if state == LoopState.COMPLETED:
            event.status = "completed"
            event.completed_at = datetime.now(UTC)
        elif state == LoopState.AWAITING_USER:
            event.status = "awaiting_user"
        elif state == LoopState.FAILED:
            event.status = "failed"
        else:
            event.status = "open"
        await event.save()
        return event

    async def _create_event(
        self,
        request: RuntimeRequest,
        event_id: str | None = None,
    ) -> AgentEvent:
        """
        创建事件。

        Args:
            request (RuntimeRequest): Runtime 请求。
            event_id (str | None): 指定事件 ID。

        Returns:
            AgentEvent: 新事件。
        """
        real_event_id = event_id or uuid4().hex
        return await AgentEvent.create(
            event_id=real_event_id,
            user_id=request.user_id,
            session_id=request.session_id or "",
            root_agent_id=str(request.metadata.get("parent_agent_id") or request.agent_id),
            status="open",
            title=self._title(request.message),
            parent_event_id=request.metadata.get("parent_event_id"),
            event_chain_id=request.metadata.get("event_chain_id") or real_event_id,
            metadata={
                "request_id": request.request_id,
                "created_by_agent_id": request.agent_id,
            },
        )

    def _title(self, message: str) -> str:
        """
        构造事件标题。

        Args:
            message (str): 用户消息。

        Returns:
            str: 事件标题。
        """
        text = " ".join(message.split())
        return text[:80]
