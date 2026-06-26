from uuid import uuid4

from fastapi import APIRouter

from runtime.engine import RuntimeEngine
from runtime.models import RuntimeRequest
from schema.api.agent import AgentRunRequest, AgentRunResponse
from schema.api.common import BaseResponse

agent_router = APIRouter(prefix="/agent", tags=["agent"])


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
