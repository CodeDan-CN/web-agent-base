import json

from exception.error_code import BizErrorCode
from runtime.context.assembler import RuntimeContext
from runtime.models import ActionDecision, ActionResult, HarnessFeedback
from runtime.state.types import LoopState
from utils.json_utils import parse_json_object
from utils.llm_client import LLMClient


class LLMHarnessEvaluator:
    """
    基于大模型的 Harness 评估器。

    Attributes:
        llm_client (LLMClient): 模型调用客户端。
    """

    def __init__(self, llm_client: LLMClient) -> None:
        """
        初始化 Harness 评估器。

        Args:
            llm_client (LLMClient): 模型调用客户端。
        """
        self.llm_client = llm_client

    async def evaluate(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
        result: ActionResult,
    ) -> HarnessFeedback:
        """
        评估 mock executor 结果。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): Action 决策。
            result (ActionResult): Action 结果。

        Returns:
            HarnessFeedback: Harness 反馈。
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(context, decision, result)
        raw = await self.llm_client.chat_text(system_prompt, user_prompt, max_tokens=2500)
        payload = parse_json_object(raw)
        return self._parse_feedback(payload)

    def _build_system_prompt(self) -> str:
        """
        构建系统提示词。

        Returns:
            str: 系统提示词。
        """
        return (
            "你是 Agent Runtime 的 LLM Harness。"
            "你只评估 call_skill 或 call_agent 的执行结果是否足以让 Loop 继续。"
            "不要按 status 简单映射，必须结合用户请求、Action 输入、缺参信息和执行结果判断。"
            "允许输出 state 只能是 ready_to_plan、missing_params、failed。"
            "必须只输出 JSON 对象，不要输出 Markdown。"
        )

    def _build_user_prompt(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
        result: ActionResult,
    ) -> str:
        """
        构建用户提示词。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): Action 决策。
            result (ActionResult): Action 结果。

        Returns:
            str: 用户提示词。
        """
        harness_instruction = context.agent_definition.files.get("harness.md", "")
        payload = {
            "user_request": {
                "message": context.request.message,
                "user_id": context.request.user_id,
                "agent_id": context.request.agent_id,
                "session_id": context.session_state.session_id,
            },
            "state_before": context.session_state.state,
            "action": decision.action.value,
            "action_detail": decision.action_detail,
            "execution_result": result.to_dict(),
            "pending_action": context.session_context.get("pending_action"),
            "missing_params": context.session_context.get("missing_params"),
            "harness_instruction": harness_instruction,
            "output_schema": {
                "state": "ready_to_plan | missing_params | failed",
                "status": "success | partial_success | missing_params | failed",
                "summary": "评估摘要",
                "missing_params": [],
                "reason": "判断原因",
            },
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _parse_feedback(self, payload: dict) -> HarnessFeedback:
        """
        解析 Harness 输出。

        Args:
            payload (dict): 模型 JSON 输出。

        Returns:
            HarnessFeedback: Harness 反馈。
        """
        try:
            state = LoopState(payload["state"])
        except (KeyError, ValueError) as exc:
            raise BizErrorCode.HARNESS_ERROR.exception("Harness state 非法") from exc
        if state not in {
            LoopState.READY_TO_PLAN,
            LoopState.MISSING_PARAMS,
            LoopState.FAILED,
        }:
            raise BizErrorCode.HARNESS_ERROR.exception("Harness state 不允许")
        missing_params = payload.get("missing_params") or []
        if not isinstance(missing_params, list):
            raise BizErrorCode.HARNESS_ERROR.exception("missing_params 必须是数组")
        return HarnessFeedback(
            state=state,
            status=str(payload.get("status", "")),
            summary=str(payload.get("summary", "")),
            missing_params=[str(item) for item in missing_params],
            reason=str(payload.get("reason", "")),
        )
