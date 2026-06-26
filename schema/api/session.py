from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    """
    创建会话请求。

    Attributes:
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        title (str | None): 会话标题。
    """

    user_id: str = Field(..., min_length=1)
    agent_id: str = Field(default="main", min_length=1)
    title: str | None = Field(default=None, max_length=128)


class SessionUpdateRequest(BaseModel):
    """
    更新会话请求。

    Attributes:
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        title (str | None): 会话标题。
    """

    user_id: str = Field(..., min_length=1)
    agent_id: str = Field(default="main", min_length=1)
    title: str | None = Field(default=None, max_length=128)


class SessionItemResponse(BaseModel):
    """
    会话列表项响应。

    Attributes:
        session_id (str): 会话 ID。
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        title (str): 会话标题。
        state (str): 当前状态。
        loop_count (int): 最近一次 Loop 次数。
        turn_count (int): 对话轮数。
        last_message (str): 最近一条用户消息。
        updated_at (datetime): 更新时间。
        created_at (datetime): 创建时间。
    """

    session_id: str
    user_id: str
    agent_id: str
    title: str
    state: str
    loop_count: int
    turn_count: int
    last_message: str = ""
    updated_at: datetime
    created_at: datetime


class SessionDetailResponse(SessionItemResponse):
    """
    会话详情响应。

    Attributes:
        pending_action (dict[str, Any] | None): 待继续动作。
        missing_params (list[str]): 缺失参数。
        conversation_summary (str): 会话摘要。
    """

    pending_action: dict[str, Any] | None = None
    missing_params: list[str] = Field(default_factory=list)
    conversation_summary: str = ""


class ConversationTurnResponse(BaseModel):
    """
    对话轮次响应。

    Attributes:
        turn_id (str): Turn ID。
        run_id (str): Run ID。
        event_id (str | None): 事件 ID。
        user_message (str): 用户消息。
        assistant_message (str): Agent 回复。
        final_state (str): 最终状态。
        created_at (datetime): 创建时间。
    """

    turn_id: str
    run_id: str
    event_id: str | None = None
    user_message: str
    assistant_message: str
    final_state: str
    created_at: datetime


class SessionDeleteResponse(BaseModel):
    """
    删除会话响应。

    Attributes:
        session_id (str): 会话 ID。
        deleted (bool): 是否已删除。
    """

    session_id: str
    deleted: bool
