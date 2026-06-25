from uuid import uuid4

from fastapi import APIRouter

from exception.error_code import BizErrorCode
from runtime.engine import RuntimeEngine
from runtime.models import RuntimeRequest
from schema.api.agent import AgentRunRequest, AgentRunResponse, SessionStateResponse
from schema.api.common import BaseResponse
from schema.db.session_state import SessionState

agent_router = APIRouter(prefix="/agent", tags=["agent"])
session_router = APIRouter(prefix="/session", tags=["session"])


@agent_router.post("/run", response_model=BaseResponse[AgentRunResponse])
async def run_agent(request: AgentRunRequest) -> BaseResponse[AgentRunResponse]:
    """
    运行 Agent。

    Args:
        request (AgentRunRequest): Agent 运行请求。

    Returns:
        BaseResponse[AgentRunResponse]: Agent 运行响应。
    """
    request_id = request.request_id or uuid4().hex
    runtime_request = RuntimeRequest(
        user_id=request.user_id,
        agent_id=request.agent_id,
        session_id=request.session_id,
        request_id=request_id,
        message=request.message,
        metadata=request.metadata,
    )
    result = await RuntimeEngine().run(runtime_request)
    response = AgentRunResponse(
        request_id=result.request_id,
        session_id=result.session_id,
        run_id=result.run_id,
        state=result.state.value,
        answer=result.answer,
        need_user_input=result.question is not None,
        question=result.question,
    )
    return BaseResponse(data=response)


@session_router.get("/{session_id}", response_model=BaseResponse[SessionStateResponse])
async def get_session(
    session_id: str,
    user_id: str,
    agent_id: str = "main",
) -> BaseResponse[SessionStateResponse]:
    """
    查询会话状态。

    Args:
        session_id (str): 会话 ID。
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。

    Returns:
        BaseResponse[SessionStateResponse]: 会话状态响应。
    """
    session_state = await SessionState.get_or_none(
        user_id=user_id,
        agent_id=agent_id,
        session_id=session_id,
    )
    if not session_state:
        raise BizErrorCode.NOT_FOUND.exception("会话不存在")
    data = SessionStateResponse(
        session_id=session_state.session_id,
        user_id=session_state.user_id,
        agent_id=session_state.agent_id,
        state=session_state.state,
        loop_count=session_state.loop_count,
        pending_action=session_state.pending_action,
        missing_params=session_state.missing_params or [],
        conversation_summary=session_state.conversation_summary or "",
    )
    return BaseResponse(data=data)
