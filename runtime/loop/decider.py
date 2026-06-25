import json

from exception.error_code import BizErrorCode
from runtime.context.assembler import RuntimeContext
from runtime.context.prompt_safety import remove_event_identifiers
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
        system_prompt = self._build_system_prompt(context)
        user_prompt = self._build_user_prompt(state, context)
        raw = await self.llm_client.chat_text(system_prompt, user_prompt, max_tokens=2500)
        payload = parse_json_object(raw)
        return self._parse_decision(payload)

    def _build_system_prompt(self, context: RuntimeContext) -> str:
        """
        构建系统提示词。

        Returns:
            str: 系统提示词。
        """
        worker_rule = (
            "当前 Agent 是 Worker Agent，禁止选择 call_agent；"
            "如需能力只能在 available_skills 中选择 call_skill，或选择 ask_user / answer_user。"
            if context.agent_definition.kind == "worker"
            else (
                "如果用户请求属于 available_workers 中某个 Worker 的领域，优先选择 call_agent。"
                "call_agent 只输出轻量 handoff，不要输出 context_package。"
                "主 Agent 不要在领域任务第一轮替 Worker 预判缺参；只要能判断归属哪个 Worker，就先 call_agent。"
                "只有无法判断应交给哪个 Worker，或任务不属于任何 Worker 且缺少信息时，才选择 ask_user。"
            )
        )
        return (
            "你是 Agent Runtime 的 LoopDecider。"
            "你只负责根据当前状态、用户输入、Agent 资产和上下文选择下一步 Action。"
            "不要直接执行工具，不要暴露 State、Action、测试等内部信息给用户。"
            "如果选择 call_skill，必须从 available_skills 中选择一个 skill_id，并提供符合其 required_input 的 input。"
            "Action input 的值必须能从 user_message、session_context、previous_action_result 或 action_history 中找到依据。"
            "如果没有足够参数调用 Skill，不要编造参数，不要用当前位置、默认值、未知等占位内容补齐必填字段，可以选择 ask_user。"
            "action_history 表示当前 run 已经完成的动作结果，可以从中继续使用早先 Skill 的输出。"
            "如果 available_skills 中存在能一次覆盖复合任务的链路 Skill，优先选择链路 Skill，不要拆成多次原子 Skill 后反复丢失上下文。"
            f"{worker_rule}"
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
        allowed_actions = self._allowed_actions(context)
        payload = {
            "current_state": state.value,
            "user_message": context.request.message,
            "request_metadata": remove_event_identifiers(context.request.metadata),
            "session_context": context.session_context,
            "harness_feedback": context.harness_feedback,
            "previous_action_result": (
                remove_event_identifiers(context.previous_action_result.to_dict())
                if context.previous_action_result
                else None
            ),
            "action_history": remove_event_identifiers(context.action_history),
            "available_skills": context.skill_catalog,
            "available_workers": context.worker_catalog,
            "allowed_actions": allowed_actions,
            "output_schema": {
                "action": "answer_user | call_skill | call_agent | ask_user",
                "action_detail": {
                    "skill_id": "call_skill 时填写 available_skills 中的 skill_id",
                    "worker_id": "call_agent 时填写 available_workers 中的 worker_id",
                    "task": "call_agent 时填写简短任务标题",
                    "handoff_context": "call_agent 时填写自然语言交接上下文",
                    "handoff": {"reason": "call_agent 时填写交给该 Worker 的原因"},
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

    def _allowed_actions(self, context: RuntimeContext) -> list[str]:
        """
        获取当前 Agent 允许的 Action。

        Args:
            context (RuntimeContext): Runtime 上下文。

        Returns:
            list[str]: Action 列表。
        """
        actions = [
            LoopAction.ANSWER_USER.value,
            LoopAction.CALL_SKILL.value,
            LoopAction.ASK_USER.value,
        ]
        if context.agent_definition.kind == "main":
            actions.insert(2, LoopAction.CALL_AGENT.value)
        return actions

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
