import json

from exception.error_code import BizErrorCode
from runtime.context.assembler import RuntimeContext
from runtime.context.prompt_safety import remove_event_identifiers
from runtime.models import ActionDecision, ActionResult, HarnessFeedback
from runtime.state.types import LoopAction
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
        评估 Skill 或 worker 结果。

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
            "如果 execution_result.data 中存在 worker_execution_report，优先把它视为 Worker 整轮执行摘要，不要只盯着 worker_result_data 的最后一次局部结果。"
            "failed 只用于代码执行失败、接口调用失败、链路执行失败、依赖不可用等执行层失败，且用户补充信息也无法补救的情况。"
            "如果执行层已经成功，但结果与用户真实意图不一致，或仍存在地址、对象、范围、时间、出行方式等可补救歧义，必须输出 missing_params，不要输出 failed。"
            "如果判断为 missing_params，尽量给出 suggested_question，便于 Loop 直接追问用户。"
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
        skill = self._skill_payload(context, decision)
        worker = self._worker_payload(context, decision)
        payload = {
            "user_request": {
                "message": context.request.message,
                "user_id": context.request.user_id,
                "agent_id": context.request.agent_id,
                "session_id": context.session_state.session_id,
            },
            "state_before": context.session_state.state,
            "action": decision.action.value,
            "action_detail": remove_event_identifiers(decision.action_detail),
            "skill": skill,
            "worker": worker,
            "execution_result": remove_event_identifiers(result.to_dict()),
            "pending_action": context.session_context.get("pending_action"),
            "missing_params": context.session_context.get("missing_params"),
            "harness_instruction": harness_instruction,
            "output_schema": {
                "state": "ready_to_plan | missing_params | failed",
                "status": "success | partial_success | missing_params | failed",
                "summary": "评估摘要",
                "missing_params": [],
                "reason": "判断原因",
                "reason_category": "execution_failure | semantic_mismatch | insufficient_information | other",
                "suggested_question": "缺参时建议追问，可选",
            },
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _skill_payload(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
    ) -> dict | None:
        """
        构建 Harness 可参考的 Skill 摘要。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): Action 决策。

        Returns:
            dict | None: Skill 摘要。
        """
        if decision.action != LoopAction.CALL_SKILL:
            return None
        raw_name = str(
            decision.action_detail.get("skill_id")
            or decision.action_detail.get("name")
            or ""
        )
        skill_id = "content_extract" if raw_name == "content_extract_skill" else raw_name
        skill = context.agent_definition.skill_registry.get(skill_id)
        return skill.to_catalog_item() if skill else None

    def _worker_payload(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
    ) -> dict | None:
        """
        构建 Harness 可参考的 Worker 摘要。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): Action 决策。

        Returns:
            dict | None: Worker 摘要。
        """
        if decision.action != LoopAction.CALL_AGENT:
            return None
        worker_id = str(
            decision.action_detail.get("worker_id")
            or decision.action_detail.get("name")
            or ""
        )
        for worker in context.worker_catalog:
            if worker.get("worker_id") == worker_id:
                return worker
        return {"worker_id": worker_id}

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
            reason_category=str(payload.get("reason_category", "")),
            suggested_question=(
                str(payload.get("suggested_question", "")).strip() or None
            ),
        )
