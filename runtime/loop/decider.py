import json

from exception.error_code import BizErrorCode
from runtime.context.assembler import RuntimeContext
from runtime.models import ActionDecision
from runtime.state.types import LoopAction, LoopState
from utils.json_utils import parse_json_object
from utils.llm_client import LLMClient


class LLMLoopDecider:
    """
    基于大模型的 Loop 决策器。

    Attributes:
        llm_client (LLMClient): 模型调用客户端。
    """

    def __init__(self, llm_client: LLMClient) -> None:
        """
        初始化 LLMLoopDecider。

        Args:
            llm_client (LLMClient): 模型调用客户端。
        """
        self.llm_client = llm_client

    async def decide(self, state: LoopState, context: RuntimeContext) -> ActionDecision:
        """
        判断下一步 Action。

        Args:
            state (LoopState): 当前状态。
            context (RuntimeContext): Runtime 上下文。

        Returns:
            ActionDecision: Action 决策。
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(state, context)
        raw = await self.llm_client.chat_text(system_prompt, user_prompt, max_tokens=2500)
        payload = parse_json_object(raw)
        return self._parse_decision(payload)

    def _build_system_prompt(self) -> str:
        """
        构建系统提示词。

        Returns:
            str: 系统提示词。
        """
        return (
            "你是 Agent Runtime 的 LoopDecider。"
            "你只负责根据当前状态、用户输入、Agent 资产和上下文选择下一步 Action。"
            "不要直接执行工具，不要暴露 State、Action、mock、测试等内部信息给用户。"
            "第一阶段只有两个外部 mock executor："
            "content_extract_skill 用于文本提取、摘要、要点整理；"
            "planning_worker 用于规划、拆解、方案、学习路线。"
            "如果信息不足，可以选择 ask_user；如果可以直接回答，选择 answer_user。"
            "如果当前状态是 missing_params 或 awaiting_user，需要先判断用户补充是否已经足够继续 call_skill 或 call_agent。"
            "必须只输出 JSON 对象，不要输出 Markdown。"
        )

    def _build_user_prompt(self, state: LoopState, context: RuntimeContext) -> str:
        """
        构建用户提示词。

        Args:
            state (LoopState): 当前状态。
            context (RuntimeContext): Runtime 上下文。

        Returns:
            str: 用户提示词。
        """
        agent_files = "\n\n".join(
            f"## {name}\n{content}"
            for name, content in context.agent_definition.files.items()
        )
        payload = {
            "current_state": state.value,
            "user_message": context.request.message,
            "session_context": context.session_context,
            "harness_feedback": context.harness_feedback,
            "previous_action_result": (
                context.previous_action_result.to_dict()
                if context.previous_action_result
                else None
            ),
            "allowed_actions": [
                LoopAction.ANSWER_USER.value,
                LoopAction.CALL_SKILL.value,
                LoopAction.CALL_AGENT.value,
                LoopAction.ASK_USER.value,
            ],
            "output_schema": {
                "action": "answer_user | call_skill | call_agent | ask_user",
                "action_detail": {
                    "name": "content_extract_skill 或 planning_worker，可选",
                    "input": "Action 输入对象，可选",
                    "question": "ask_user 时的追问，可选",
                    "answer_instruction": "answer_user 时的回答要求，可选",
                },
                "reason": "简短原因",
            },
        }
        return (
            f"Agent 文件：\n{agent_files}\n\n"
            f"请基于以下 JSON 判断下一步 Action：\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

    def _parse_decision(self, payload: dict) -> ActionDecision:
        """
        解析模型决策。

        Args:
            payload (dict): 模型 JSON 输出。

        Returns:
            ActionDecision: Action 决策。
        """
        try:
            action = LoopAction(payload["action"])
        except (KeyError, ValueError) as exc:
            raise BizErrorCode.ACTION_PARSE_ERROR.exception("Loop Action 非法") from exc
        action_detail = payload.get("action_detail") or {}
        if not isinstance(action_detail, dict):
            raise BizErrorCode.ACTION_PARSE_ERROR.exception("action_detail 必须是对象")
        return ActionDecision(
            action=action,
            action_detail=action_detail,
            reason=str(payload.get("reason", "")),
        )
