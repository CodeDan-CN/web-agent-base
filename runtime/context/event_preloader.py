import json
import logging
from dataclasses import dataclass, field
from typing import Any

from schema.db.agent_event import AgentEvent, AgentEventContext, AgentEventRun
from schema.db.agent_run import AgentRun
from utils.json_utils import parse_json_object
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class EventPromptContext:
    """
    Loop 前可注入 Prompt 的事件对话上下文。

    Attributes:
        should_inject (bool): 是否注入事件对话。
        event_dialogues (list[dict[str, str]]): 命中事件内的一轮或多轮对话。
        source (str): 上下文来源，仅 Runtime 内部使用。
        matched_event_id (str): 命中事件 ID，仅 Runtime 内部使用。
    """

    should_inject: bool = False
    event_dialogues: list[dict[str, str]] = field(default_factory=list)
    source: str = "empty"
    matched_event_id: str = ""

    def to_prompt_dict(self) -> dict[str, Any]:
        """
        转换为允许进入 Prompt 的字典。

        Returns:
            dict[str, Any]: Prompt 安全上下文。
        """
        return {
            "should_inject": self.should_inject,
            "event_dialogues": self.event_dialogues,
        }


class EventContextPreloader:
    """
    Loop 前事件上下文预加载器。
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        """
        初始化事件上下文预加载器。

        Args:
            llm_client (LLMClient | None): 模型客户端。
        """
        self.llm_client = llm_client or LLMClient()

    async def preload(
        self,
        user_id: str,
        session_id: str,
        agent_id: str,
        event_id: str,
        user_message: str,
        explicit_event_id: bool,
        allow_related_lookup: bool,
        exclude_run_id: str | None = None,
    ) -> EventPromptContext:
        """
        预加载当前 Loop 可用的事件对话。

        Args:
            user_id (str): 用户 ID。
            session_id (str): 会话 ID。
            agent_id (str): Agent ID。
            event_id (str): 当前事件 ID。
            user_message (str): 当前用户消息。
            explicit_event_id (bool): 请求是否显式传入事件 ID。
            allow_related_lookup (bool): 是否允许当前会话历史事件相关性判断。
            exclude_run_id (str | None): 需要排除的当前 run ID。

        Returns:
            EventPromptContext: Prompt 可用事件对话上下文。
        """
        if event_id:
            context = await self._context_for_event(
                event_id=event_id,
                agent_id=agent_id,
                source="explicit_event" if explicit_event_id else "current_event",
                exclude_run_id=exclude_run_id,
            )
            if context.should_inject or explicit_event_id:
                return context
        if not allow_related_lookup:
            return EventPromptContext()
        return await self._context_from_related_session_event(
            user_id=user_id,
            session_id=session_id,
            agent_id=agent_id,
            current_event_id=event_id,
            user_message=user_message,
        )

    async def _context_for_event(
        self,
        event_id: str,
        agent_id: str,
        source: str,
        exclude_run_id: str | None = None,
    ) -> EventPromptContext:
        """
        读取指定事件内当前 Agent 相关对话。

        Args:
            event_id (str): 事件 ID。
            agent_id (str): Agent ID。
            source (str): 来源标识。
            exclude_run_id (str | None): 需要排除的 run ID。

        Returns:
            EventPromptContext: 事件对话上下文。
        """
        dialogues = await self._event_dialogues(event_id, agent_id, exclude_run_id)
        return EventPromptContext(
            should_inject=bool(dialogues),
            event_dialogues=dialogues,
            source=source if dialogues else "empty",
            matched_event_id=event_id if dialogues else "",
        )

    async def _context_from_related_session_event(
        self,
        user_id: str,
        session_id: str,
        agent_id: str,
        current_event_id: str,
        user_message: str,
    ) -> EventPromptContext:
        """
        从当前会话历史事件中判断并读取相关事件对话。

        Args:
            user_id (str): 用户 ID。
            session_id (str): 会话 ID。
            agent_id (str): Agent ID。
            current_event_id (str): 当前事件 ID。
            user_message (str): 当前用户消息。

        Returns:
            EventPromptContext: 事件对话上下文。
        """
        candidates = await self._candidate_events(user_id, session_id, agent_id, current_event_id)
        if not candidates:
            return EventPromptContext()
        matched_event_id = await self._match_related_event(user_message, candidates)
        if not matched_event_id:
            return EventPromptContext()
        return await self._context_for_event(
            event_id=matched_event_id,
            agent_id=agent_id,
            source="related_session_event",
        )

    async def _candidate_events(
        self,
        user_id: str,
        session_id: str,
        agent_id: str,
        current_event_id: str,
    ) -> list[dict[str, str]]:
        """
        读取当前会话下可用于相关性判断的候选事件。

        Args:
            user_id (str): 用户 ID。
            session_id (str): 会话 ID。
            agent_id (str): Agent ID。
            current_event_id (str): 当前事件 ID。

        Returns:
            list[dict[str, str]]: 候选事件摘要。
        """
        events = (
            await AgentEvent.filter(user_id=user_id, session_id=session_id)
            .exclude(event_id=current_event_id)
            .order_by("-updated_at")
            .limit(5)
        )
        candidates: list[dict[str, str]] = []
        for event in events:
            context = await AgentEventContext.get_or_none(
                event_id=event.event_id,
                agent_id=agent_id,
            )
            summary = context.summary if context else ""
            candidates.append(
                {
                    "event_id": event.event_id,
                    "title": event.title or "",
                    "summary": summary[:300],
                    "status": event.status,
                    "updated_at": event.updated_at.isoformat(),
                }
            )
        return candidates

    async def _match_related_event(
        self,
        user_message: str,
        candidates: list[dict[str, str]],
    ) -> str:
        """
        使用模型判断当前消息是否延续某个候选事件。

        Args:
            user_message (str): 当前用户消息。
            candidates (list[dict[str, str]]): 候选事件。

        Returns:
            str: 命中的事件 ID，没有命中时为空字符串。
        """
        system_prompt = (
            "你是事件相关性判断器。"
            "只判断当前用户消息是否在延续候选事件中的一个。"
            "必须只输出 JSON 对象，不要输出 Markdown。"
        )
        user_prompt = json.dumps(
            {
                "user_message": user_message,
                "candidates": candidates,
                "output_schema": {
                    "related": "boolean",
                    "event_id": "相关时填写候选 event_id，否则为空字符串",
                    "confidence": "possible | unrelated",
                    "reason": "简短原因",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        try:
            raw = await self.llm_client.chat_text(system_prompt, user_prompt, max_tokens=800)
            payload = parse_json_object(raw)
        except Exception:
            logger.exception("Event relatedness check failed")
            return ""
        if payload.get("related") is not True:
            return ""
        matched_event_id = str(payload.get("event_id") or "").strip()
        candidate_ids = {candidate["event_id"] for candidate in candidates}
        return matched_event_id if matched_event_id in candidate_ids else ""

    async def _event_dialogues(
        self,
        event_id: str,
        agent_id: str,
        exclude_run_id: str | None = None,
    ) -> list[dict[str, str]]:
        """
        读取事件内当前 Agent 最近几轮对话。

        Args:
            event_id (str): 事件 ID。
            agent_id (str): Agent ID。
            exclude_run_id (str | None): 需要排除的 run ID。

        Returns:
            list[dict[str, str]]: 最近对话。
        """
        links = (
            await AgentEventRun.filter(event_id=event_id, agent_id=agent_id)
            .order_by("-created_at")
            .limit(6)
        )
        dialogues: list[dict[str, str]] = []
        for link in reversed(links):
            if exclude_run_id and link.run_id == exclude_run_id:
                continue
            run = await AgentRun.get_or_none(id=link.run_id)
            if not run:
                continue
            if not run.user_message and not run.final_answer:
                continue
            dialogues.append(
                {
                    "user": run.user_message,
                    "assistant": run.final_answer or "",
                }
            )
        return dialogues
