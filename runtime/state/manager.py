from uuid import uuid4

from runtime.models import ActionDecision, ActionResult, HarnessFeedback, RuntimeRequest
from runtime.state.types import LoopAction, LoopState
from schema.db.session_state import SessionState


class StateManager:
    """
    会话状态管理器。
    """

    async def load_or_create_session(self, request: RuntimeRequest) -> SessionState:
        """
        读取或创建会话状态。

        Args:
            request (RuntimeRequest): Runtime 请求。

        Returns:
            SessionState: 会话状态。
        """
        session_id = request.session_id or uuid4().hex
        existing = await SessionState.get_or_none(
            user_id=request.user_id,
            agent_id=request.agent_id,
            session_id=session_id,
        )
        if existing:
            return existing
        state = SessionState(
            id=uuid4().hex,
            session_id=session_id,
            user_id=request.user_id,
            agent_id=request.agent_id,
            state=LoopState.NEW_REQUEST.value,
            loop_count=0,
            pending_action=None,
            missing_params=[],
            conversation_summary="",
        )
        await state.save()
        return state

    def state_for_new_run(self, session_state: SessionState) -> LoopState:
        """
        计算新 run 的初始状态。

        Args:
            session_state (SessionState): 会话状态。

        Returns:
            LoopState: 初始状态。
        """
        if session_state.state == LoopState.AWAITING_USER.value:
            return LoopState.AWAITING_USER
        return LoopState.NEW_REQUEST

    def next_state_for_direct_action(self, action: LoopAction) -> LoopState:
        """
        计算不进入 Harness 的 Action 下一状态。

        Args:
            action (LoopAction): Action。

        Returns:
            LoopState: 下一状态。
        """
        if action == LoopAction.ANSWER_USER:
            return LoopState.COMPLETED
        if action == LoopAction.ASK_USER:
            return LoopState.AWAITING_USER
        return LoopState.FAILED

    async def flush_boundary_state(
        self,
        session_state: SessionState,
        state: LoopState,
        loop_count: int,
        pending_action: ActionDecision | None,
        missing_params: list[str],
        result: ActionResult | None,
        user_message: str,
    ) -> None:
        """
        边界状态写回会话快照。

        Args:
            session_state (SessionState): 会话状态。
            state (LoopState): 当前状态。
            loop_count (int): Loop 次数。
            pending_action (ActionDecision | None): 待继续动作。
            missing_params (list[str]): 缺失参数。
            result (ActionResult | None): 动作结果。
            user_message (str): 用户消息。
        """
        session_state.state = state.value
        session_state.loop_count = loop_count
        session_state.pending_action = (
            {
                "action": pending_action.action.value,
                "action_detail": pending_action.action_detail,
                "reason": pending_action.reason,
            }
            if state == LoopState.AWAITING_USER and pending_action
            else None
        )
        session_state.missing_params = (
            missing_params if state == LoopState.AWAITING_USER else []
        )
        await session_state.save()

    def missing_params_from_feedback(
        self,
        feedback: HarnessFeedback | None,
        result: ActionResult | None,
    ) -> list[str]:
        """
        从 Harness 或执行结果中提取缺参信息。

        Args:
            feedback (HarnessFeedback | None): Harness 反馈。
            result (ActionResult | None): Action 结果。

        Returns:
            list[str]: 缺失参数。
        """
        if feedback and feedback.missing_params:
            return feedback.missing_params
        if result and result.missing_params:
            return result.missing_params
        return []
