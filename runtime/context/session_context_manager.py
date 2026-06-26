from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from runtime.context.context_deduplicator import ContextDeduplicator
from runtime.context.prompt_safety import remove_event_identifiers
from runtime.context.session_context_compressor import SessionContextCompressor
from runtime.context.token_estimator import estimate_turn_tokens
from schema.db.conversation_turn import ConversationTurn
from schema.db.session_state import SessionState
from utils.config import get_settings


class SessionContextManager:
    """
    当前 session 会话上下文管理器。
    """

    def __init__(
        self,
        compressor: SessionContextCompressor | None = None,
        deduplicator: ContextDeduplicator | None = None,
    ) -> None:
        """
        初始化会话上下文管理器。

        Args:
            compressor (SessionContextCompressor | None): 会话摘要压缩器。
            deduplicator (ContextDeduplicator | None): 上下文去重器。
        """
        self.compressor = compressor or SessionContextCompressor()
        self.deduplicator = deduplicator or ContextDeduplicator()

    async def record_turn(
        self,
        run_id: str,
        session_id: str,
        user_id: str,
        agent_id: str,
        event_id: str,
        user_message: str,
        assistant_message: str,
        final_state: str,
    ) -> ConversationTurn:
        """
        记录一轮用户可见对话。

        Args:
            run_id (str): AgentRun ID。
            session_id (str): 会话 ID。
            user_id (str): 用户 ID。
            agent_id (str): Agent ID。
            event_id (str): 事件 ID。
            user_message (str): 用户输入。
            assistant_message (str): Agent 回复或追问。
            final_state (str): 最终状态。

        Returns:
            ConversationTurn: 对话记录。
        """
        existing = await ConversationTurn.get_or_none(run_id=run_id)
        if existing:
            return existing
        return await ConversationTurn.create(
            id=uuid4().hex,
            turn_id=uuid4().hex,
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            event_id=event_id or None,
            user_message=user_message,
            assistant_message=assistant_message,
            final_state=final_state,
            token_estimate=estimate_turn_tokens(user_message, assistant_message),
        )

    async def build_session_context(
        self,
        session_state: SessionState,
        event_dialogues: list[dict[str, Any]],
        exclude_run_id: str | None = None,
    ) -> dict[str, Any]:
        """
        构建当前 Prompt 可用的会话上下文片段。

        Args:
            session_state (SessionState): 会话状态。
            event_dialogues (list[dict[str, Any]]): 事件命中的原始对话。
            exclude_run_id (str | None): 需要排除的当前 run ID。

        Returns:
            dict[str, Any]: Prompt 安全会话上下文片段。
        """
        recent_turns = await self.recent_turns(session_state, exclude_run_id)
        event_dialogues_deduped = self.deduplicator.dedupe_event_dialogues(
            recent_turns,
            event_dialogues,
        )
        return {
            "conversation_summary": session_state.conversation_summary or "",
            "recent_turns": self._prompt_turns(recent_turns),
            "event_context": {
                "should_inject": bool(event_dialogues_deduped),
                "event_dialogues": self._prompt_turns(event_dialogues_deduped),
            },
        }

    async def recent_turns(
        self,
        session_state: SessionState,
        exclude_run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        读取当前 session 最近原始对话。

        Args:
            session_state (SessionState): 会话状态。
            exclude_run_id (str | None): 需要排除的当前 run ID。

        Returns:
            list[dict[str, Any]]: 最近原始对话。
        """
        settings = get_settings()
        query = ConversationTurn.filter(
            user_id=session_state.user_id,
            agent_id=session_state.agent_id,
            session_id=session_state.session_id,
            summarized_at__isnull=True,
        )
        if exclude_run_id:
            query = query.exclude(run_id=exclude_run_id)
        turns = await query.order_by("-created_at").limit(settings.session_recent_turn_max_count)
        return [self._turn_to_dict(turn) for turn in reversed(turns)]

    async def compress_if_needed(
        self,
        user_id: str,
        agent_id: str,
        session_id: str,
    ) -> None:
        """
        如果当前 session 原始对话超过预算，则压缩较早对话。

        Args:
            user_id (str): 用户 ID。
            agent_id (str): Agent ID。
            session_id (str): 会话 ID。
        """
        settings = get_settings()
        turns = await ConversationTurn.filter(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            summarized_at__isnull=True,
        ).order_by("created_at")
        raw_tokens = sum(turn.token_estimate for turn in turns)
        trigger_tokens = int(
            settings.session_context_max_tokens * settings.session_summary_trigger_ratio
        )
        if raw_tokens < trigger_tokens:
            return
        selected = self._select_turns_to_compress(turns)
        if not selected:
            return
        session_state = await SessionState.get_or_none(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
        )
        if not session_state:
            return
        summary = await self.compressor.compress(
            previous_summary=session_state.conversation_summary or "",
            turns=selected,
            target_tokens=settings.session_summary_target_tokens,
        )
        batch_id = uuid4().hex
        now = datetime.now(UTC)
        session_state.conversation_summary = summary
        await session_state.save()
        for turn in selected:
            turn.summary_batch_id = batch_id
            turn.summarized_at = now
            await turn.save()

    def _select_turns_to_compress(
        self,
        turns: list[ConversationTurn],
    ) -> list[ConversationTurn]:
        """
        选择本次要压缩的较早对话。

        Args:
            turns (list[ConversationTurn]): 未压缩原始对话。

        Returns:
            list[ConversationTurn]: 待压缩对话。
        """
        settings = get_settings()
        protected_count = settings.session_recent_turn_min_count
        if len(turns) <= protected_count:
            return []
        target_tokens = int(
            settings.session_context_max_tokens
            * settings.session_summary_target_after_compression_ratio
        )
        remaining_tokens = sum(turn.token_estimate for turn in turns)
        candidates = turns[: -protected_count]
        selected: list[ConversationTurn] = []
        for turn in candidates:
            if len(selected) >= settings.session_turn_compress_batch_size:
                break
            selected.append(turn)
            remaining_tokens -= turn.token_estimate
            if remaining_tokens <= target_tokens:
                break
        return selected

    def _turn_to_dict(self, turn: ConversationTurn) -> dict[str, Any]:
        """
        转换数据库 turn 为内部对话字典。

        Args:
            turn (ConversationTurn): 数据库对话记录。

        Returns:
            dict[str, Any]: 内部对话字典。
        """
        return {
            "turn_id": turn.turn_id,
            "run_id": turn.run_id,
            "event_id": turn.event_id or "",
            "agent_id": turn.agent_id,
            "user": turn.user_message,
            "assistant": turn.assistant_message,
            "final_state": turn.final_state,
            "token_estimate": turn.token_estimate,
        }

    def _prompt_turns(self, turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        生成 Prompt 安全对话列表。

        Args:
            turns (list[dict[str, Any]]): 内部对话列表。

        Returns:
            list[dict[str, Any]]: Prompt 安全对话列表。
        """
        return remove_event_identifiers(
            [
                {
                    "turn_id": turn.get("turn_id", ""),
                    "run_id": turn.get("run_id", ""),
                    "event_id": turn.get("event_id", ""),
                    "agent_id": turn.get("agent_id", ""),
                    "user": turn.get("user") or turn.get("user_message") or "",
                    "assistant": turn.get("assistant")
                    or turn.get("assistant_message")
                    or "",
                    "final_state": turn.get("final_state", ""),
                }
                for turn in turns
            ]
        )
