from enum import StrEnum


class LoopState(StrEnum):
    """
    Agent Loop 状态。

    Attributes:
        NEW_REQUEST: 新请求。
        READY_TO_PLAN: 可继续规划。
        MISSING_PARAMS: 缺少参数。
        AWAITING_USER: 等待用户输入。
        COMPLETED: 已完成。
        FAILED: 已失败。
    """

    NEW_REQUEST = "new_request"
    READY_TO_PLAN = "ready_to_plan"
    MISSING_PARAMS = "missing_params"
    AWAITING_USER = "awaiting_user"
    COMPLETED = "completed"
    FAILED = "failed"


class LoopAction(StrEnum):
    """
    Agent Loop 动作。

    Attributes:
        ANSWER_USER: 回答用户。
        CALL_SKILL: 调用 Skill executor。
        CALL_AGENT: 调用 worker executor。
        ASK_USER: 追问用户。
    """

    ANSWER_USER = "answer_user"
    CALL_SKILL = "call_skill"
    CALL_AGENT = "call_agent"
    ASK_USER = "ask_user"
