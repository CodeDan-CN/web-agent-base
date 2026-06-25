from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    """
    Agent 运行请求。

    Attributes:
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        session_id (str | None): 会话 ID。
        request_id (str | None): 请求 ID。
        message (str): 用户消息。
        metadata (dict[str, Any]): 附加元数据。
    """

    user_id: str = Field(..., min_length=1)
    agent_id: str = Field(default="main", min_length=1)
    session_id: str | None = None
    request_id: str | None = None
    message: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    """
    Agent 运行响应。

    Attributes:
        request_id (str): 请求 ID。
        session_id (str): 会话 ID。
        run_id (str): 运行 ID。
        state (str): 最终状态。
        answer (str | None): 回答内容。
        need_user_input (bool): 是否需要用户继续输入。
        question (str | None): 追问内容。
    """

    request_id: str
    session_id: str
    run_id: str
    state: str
    answer: str | None = None
    need_user_input: bool = False
    question: str | None = None


class SessionStateResponse(BaseModel):
    """
    会话状态响应。

    Attributes:
        session_id (str): 会话 ID。
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        state (str): 当前状态。
        loop_count (int): 最近一次 Loop 次数。
        pending_action (dict[str, Any] | None): 待继续动作。
        missing_params (list[str]): 缺失参数。
        conversation_summary (str): 轻量会话摘要。
    """

    session_id: str
    user_id: str
    agent_id: str
    state: str
    loop_count: int
    pending_action: dict[str, Any] | None = None
    missing_params: list[str] = Field(default_factory=list)
    conversation_summary: str = ""
