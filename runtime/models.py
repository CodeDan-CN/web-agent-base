from dataclasses import dataclass, field
from typing import Any

from runtime.state.types import LoopAction, LoopState


@dataclass
class RuntimeRequest:
    """
    Runtime 内部请求。

    Attributes:
        user_id (str): 用户 ID。
        agent_id (str): Agent ID。
        session_id (str | None): 会话 ID。
        request_id (str): 请求 ID。
        message (str): 用户消息。
        metadata (dict[str, Any]): 附加元数据。
    """

    user_id: str
    agent_id: str
    session_id: str | None
    request_id: str
    message: str
    metadata: dict[str, Any]


@dataclass
class ActionDecision:
    """
    Loop 动作决策。

    Attributes:
        action (LoopAction): 下一步动作。
        action_detail (dict[str, Any]): 动作详情。
        reason (str): 决策原因。
    """

    action: LoopAction
    action_detail: dict[str, Any]
    reason: str = ""


@dataclass
class ActionResult:
    """
    动作执行结果。

    Attributes:
        status (str): 执行状态。
        data (Any): 执行数据。
        summary (str): 摘要。
        answer (str | None): 回答内容。
        question (str | None): 追问内容。
        missing_params (list[str]): 缺失参数。
        error (str | None): 错误信息。
    """

    status: str
    data: Any = field(default_factory=dict)
    summary: str = ""
    answer: str | None = None
    question: str | None = None
    missing_params: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        转换为可 JSON 序列化字典。

        Returns:
            dict[str, Any]: 字典结果。
        """
        return {
            "status": self.status,
            "data": self.data,
            "summary": self.summary,
            "answer": self.answer,
            "question": self.question,
            "missing_params": self.missing_params,
            "error": self.error,
        }


@dataclass
class HarnessFeedback:
    """
    Harness 评估结果。

    Attributes:
        state (LoopState): 下一状态。
        status (str): 评估状态。
        summary (str): 评估摘要。
        missing_params (list[str]): 缺失参数。
        reason (str): 评估原因。
        reason_category (str): 原因分类。
        suggested_question (str | None): 建议追问。
    """

    state: LoopState
    status: str
    summary: str
    missing_params: list[str] = field(default_factory=list)
    reason: str = ""
    reason_category: str = ""
    suggested_question: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        转换为可 JSON 序列化字典。

        Returns:
            dict[str, Any]: 字典结果。
        """
        return {
            "state": self.state.value,
            "status": self.status,
            "summary": self.summary,
            "missing_params": self.missing_params,
            "reason": self.reason,
            "reason_category": self.reason_category,
            "suggested_question": self.suggested_question,
        }


@dataclass
class RuntimeResult:
    """
    Runtime 运行结果。

    Attributes:
        request_id (str): 请求 ID。
        session_id (str): 会话 ID。
        run_id (str): 运行 ID。
        state (LoopState): 最终状态。
        answer (str | None): 回答内容。
        question (str | None): 追问内容。
        data (Any): 完成态结构化结果。
        summary (str): 完成态摘要。
    """

    request_id: str
    session_id: str
    run_id: str
    state: LoopState
    answer: str | None = None
    question: str | None = None
    data: Any = field(default_factory=dict)
    summary: str = ""
