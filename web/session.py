from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter

from exception.error_code import BizErrorCode
from runtime.state.types import LoopState
from schema.api.common import BaseResponse
from schema.api.session import (
    ConversationTurnResponse,
    SessionCreateRequest,
    SessionDeleteResponse,
    SessionDetailResponse,
    SessionItemResponse,
    SessionUpdateRequest,
)
from schema.db.conversation_turn import ConversationTurn
from schema.db.session_state import SessionState

session_router = APIRouter(prefix="/sessions", tags=["session"])


@session_router.post("", response_model=BaseResponse[SessionDetailResponse])
async def create_session(
    request: SessionCreateRequest,
) -> BaseResponse[SessionDetailResponse]:
    """
    创建会话。

    Args:
        request (SessionCreateRequest): 创建会话请求。

    Returns:
        BaseResponse[SessionDetailResponse]: 会话详情响应。
    """
    session = await SessionState.create(
        id=uuid4().hex,
        session_id=uuid4().hex,
        user_id=request.user_id,
        agent_id=request.agent_id,
        title=_normalize_title(request.title),
        state=LoopState.NEW_REQUEST.value,
        loop_count=0,
        pending_action=None,
        missing_params=[],
        conversation_summary="",
    )
    return BaseResponse(data=await _session_detail(session))


@session_router.get("", response_model=BaseResponse[list[SessionItemResponse]])
async def list_sessions(
    user_id: str,
    agent_id: str = "main",
) -> BaseResponse[list[SessionItemResponse]]:
    """
    查询用户在指定 Agent 下的会话列表。

    Args:
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。

    Returns:
        BaseResponse[list[SessionItemResponse]]: 会话列表响应。
    """
    sessions = (
        await SessionState.filter(
            user_id=user_id,
            agent_id=agent_id,
            deleted_at__isnull=True,
        )
        .order_by("-updated_at")
        .all()
    )
    return BaseResponse(data=[await _session_item(session) for session in sessions])


@session_router.get(
    "/{session_id}",
    response_model=BaseResponse[SessionDetailResponse],
)
async def get_session(
    session_id: str,
    user_id: str,
    agent_id: str = "main",
) -> BaseResponse[SessionDetailResponse]:
    """
    查询会话详情。

    Args:
        session_id (str): 会话 ID。
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。

    Returns:
        BaseResponse[SessionDetailResponse]: 会话详情响应。
    """
    session = await _get_active_session(user_id, agent_id, session_id)
    return BaseResponse(data=await _session_detail(session))


@session_router.patch(
    "/{session_id}",
    response_model=BaseResponse[SessionDetailResponse],
)
async def update_session(
    session_id: str,
    request: SessionUpdateRequest,
) -> BaseResponse[SessionDetailResponse]:
    """
    更新会话。

    Args:
        session_id (str): 会话 ID。
        request (SessionUpdateRequest): 更新会话请求。

    Returns:
        BaseResponse[SessionDetailResponse]: 会话详情响应。
    """
    session = await _get_active_session(request.user_id, request.agent_id, session_id)
    if request.title is not None:
        session.title = _normalize_title(request.title)
    await session.save()
    return BaseResponse(data=await _session_detail(session))


@session_router.delete(
    "/{session_id}",
    response_model=BaseResponse[SessionDeleteResponse],
)
async def delete_session(
    session_id: str,
    user_id: str,
    agent_id: str = "main",
) -> BaseResponse[SessionDeleteResponse]:
    """
    删除会话。

    Args:
        session_id (str): 会话 ID。
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。

    Returns:
        BaseResponse[SessionDeleteResponse]: 删除响应。
    """
    session = await _get_active_session(user_id, agent_id, session_id)
    session.deleted_at = datetime.now(UTC)
    await session.save()
    return BaseResponse(data=SessionDeleteResponse(session_id=session_id, deleted=True))


@session_router.get(
    "/{session_id}/turns",
    response_model=BaseResponse[list[ConversationTurnResponse]],
)
async def list_session_turns(
    session_id: str,
    user_id: str,
    agent_id: str = "main",
) -> BaseResponse[list[ConversationTurnResponse]]:
    """
    查询会话对话记录。

    Args:
        session_id (str): 会话 ID。
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。

    Returns:
        BaseResponse[list[ConversationTurnResponse]]: 对话记录响应。
    """
    await _get_active_session(user_id, agent_id, session_id)
    turns = (
        await ConversationTurn.filter(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
        )
        .order_by("created_at")
        .all()
    )
    return BaseResponse(
        data=[
            ConversationTurnResponse(
                turn_id=turn.turn_id,
                run_id=turn.run_id,
                event_id=turn.event_id,
                user_message=turn.user_message,
                assistant_message=turn.assistant_message,
                final_state=turn.final_state,
                created_at=turn.created_at,
            )
            for turn in turns
        ]
    )


async def _get_active_session(
    user_id: str,
    agent_id: str,
    session_id: str,
) -> SessionState:
    """
    查询未删除会话。

    Args:
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        session_id (str): 会话 ID。

    Returns:
        SessionState: 会话状态。
    """
    session = await SessionState.get_or_none(
        user_id=user_id,
        agent_id=agent_id,
        session_id=session_id,
        deleted_at__isnull=True,
    )
    if not session:
        raise BizErrorCode.NOT_FOUND.exception("会话不存在")
    return session


async def _session_item(session: SessionState) -> SessionItemResponse:
    """
    转换会话列表项。

    Args:
        session (SessionState): 会话状态。

    Returns:
        SessionItemResponse: 会话列表项。
    """
    turn_count = await ConversationTurn.filter(
        user_id=session.user_id,
        agent_id=session.agent_id,
        session_id=session.session_id,
    ).count()
    last_turn = (
        await ConversationTurn.filter(
            user_id=session.user_id,
            agent_id=session.agent_id,
            session_id=session.session_id,
        )
        .order_by("-created_at")
        .first()
    )
    return SessionItemResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        agent_id=session.agent_id,
        title=session.title,
        state=session.state,
        loop_count=session.loop_count,
        turn_count=turn_count,
        last_message=last_turn.user_message if last_turn else "",
        updated_at=session.updated_at,
        created_at=session.created_at,
    )


async def _session_detail(session: SessionState) -> SessionDetailResponse:
    """
    转换会话详情。

    Args:
        session (SessionState): 会话状态。

    Returns:
        SessionDetailResponse: 会话详情。
    """
    item = await _session_item(session)
    return SessionDetailResponse(
        **item.model_dump(),
        pending_action=session.pending_action,
        missing_params=session.missing_params or [],
        conversation_summary=session.conversation_summary or "",
    )


def _normalize_title(title: str | None) -> str:
    """
    规范化会话标题。

    Args:
        title (str | None): 原始标题。

    Returns:
        str: 会话标题。
    """
    normalized = (title or "").strip()
    if not normalized:
        return "新会话"
    return normalized[:128]
