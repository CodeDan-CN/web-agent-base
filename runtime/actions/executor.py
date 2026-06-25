from exception.error_code import BizErrorCode
from runtime.ag_ui.adapter import AGUIEventAdapter
from runtime.context.assembler import RuntimeContext
from runtime.context.prompt_safety import remove_event_identifiers
from runtime.models import ActionDecision, ActionResult
from runtime.state.types import LoopAction
from runtime.tools.skill_executor import SkillExecutor
from runtime.workers.worker_executor import WorkerExecutor
from utils.llm_client import LLMClient


class ActionExecutor:
    """
    Loop Action 执行器。

    Attributes:
        llm_client (LLMClient): 模型调用客户端。
        skill_executor (SkillExecutor): Skill 执行器。
        worker_executor (WorkerExecutor): Worker Agent 执行器。
    """

    def __init__(self, llm_client: LLMClient) -> None:
        """
        初始化 ActionExecutor。

        Args:
            llm_client (LLMClient): 模型调用客户端。
        """
        self.llm_client = llm_client
        self.skill_executor = SkillExecutor()
        self.worker_executor = WorkerExecutor()

    async def execute(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
        agui_adapter: AGUIEventAdapter | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
    ) -> ActionResult:
        """
        执行 Action。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): Action 决策。
            agui_adapter (AGUIEventAdapter | None): AG-UI 适配器。
            run_id (str | None): Run ID。
            session_id (str | None): Session ID。

        Returns:
            ActionResult: Action 结果。
        """
        if decision.action == LoopAction.ANSWER_USER:
            return await self._answer_user(
                context,
                decision,
                agui_adapter,
                run_id,
                session_id,
            )
        if decision.action == LoopAction.ASK_USER:
            return self._ask_user(decision)
        if decision.action == LoopAction.CALL_SKILL:
            return await self._call_skill(context, decision)
        if decision.action == LoopAction.CALL_AGENT:
            return await self._call_agent(context, decision)
        raise BizErrorCode.ACTION_EXECUTE_ERROR.exception("不支持的 Action")

    async def _answer_user(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
        agui_adapter: AGUIEventAdapter | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
    ) -> ActionResult:
        """
        生成用户回答。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): Action 决策。
            agui_adapter (AGUIEventAdapter | None): AG-UI 适配器。
            run_id (str | None): Run ID。
            session_id (str | None): Session ID。

        Returns:
            ActionResult: 回答结果。
        """
        system_prompt = (
            "你是当前 Agent 的最终回答生成器。"
            "请根据用户请求、Agent 文件、上下文和上一轮执行结果自然回答。"
            "不要暴露 State、Action、mock、测试、Harness 等内部实现细节。"
        )
        user_prompt = self._build_answer_prompt(context, decision)
        if agui_adapter and run_id and session_id:
            answer = await self._answer_user_stream(
                system_prompt,
                user_prompt,
                agui_adapter,
                run_id,
                session_id,
            )
            return ActionResult(status="success", answer=answer, summary="已生成回答")
        answer = await self.llm_client.chat_text(system_prompt, user_prompt, max_tokens=3000)
        return ActionResult(status="success", answer=answer, summary="已生成回答")

    async def _answer_user_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        agui_adapter: AGUIEventAdapter,
        run_id: str,
        session_id: str,
    ) -> str:
        """
        流式生成用户回答并输出 AG-UI 文本事件。

        Args:
            system_prompt (str): system prompt。
            user_prompt (str): user prompt。
            agui_adapter (AGUIEventAdapter): AG-UI 适配器。
            run_id (str): Run ID。
            session_id (str): Session ID。

        Returns:
            str: 完整回答。
        """
        message_id = agui_adapter.new_message_id()
        chunks: list[str] = []
        await agui_adapter.emit(agui_adapter.text_message_start(run_id, session_id, message_id))
        async for chunk in self.llm_client.chat_text_stream(
            system_prompt,
            user_prompt,
            max_tokens=3000,
        ):
            chunks.append(chunk)
            await agui_adapter.emit(
                agui_adapter.text_message_content(run_id, session_id, message_id, chunk)
            )
        await agui_adapter.emit(agui_adapter.text_message_end(run_id, session_id, message_id))
        return "".join(chunks)

    def _ask_user(self, decision: ActionDecision) -> ActionResult:
        """
        生成追问结果。

        Args:
            decision (ActionDecision): Action 决策。

        Returns:
            ActionResult: 追问结果。
        """
        question = str(decision.action_detail.get("question") or "").strip()
        if not question:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception("ask_user 缺少 question")
        return ActionResult(status="success", question=question, summary="等待用户补充")

    async def _call_skill(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
    ) -> ActionResult:
        """
        调用 Skill executor。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): Action 决策。

        Returns:
            ActionResult: Skill 执行结果。
        """
        return await self.skill_executor.execute(context, decision)

    async def _call_agent(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
    ) -> ActionResult:
        """
        调用 Worker Agent executor。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): Action 决策。

        Returns:
            ActionResult: worker executor 结果。
        """
        return await self.worker_executor.execute(context, decision)

    def _build_answer_prompt(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
    ) -> str:
        """
        构建回答生成提示词。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): Action 决策。

        Returns:
            str: 回答生成提示词。
        """
        files = "\n\n".join(
            f"## {name}\n{content}"
            for name, content in context.agent_definition.files.items()
        )
        previous_result = (
            remove_event_identifiers(context.previous_action_result.to_dict())
            if context.previous_action_result
            else None
        )
        return (
            f"Agent 文件：\n{files}\n\n"
            f"用户请求：{context.request.message}\n\n"
            f"请求元数据：{remove_event_identifiers(context.request.metadata)}\n\n"
            f"会话上下文：{context.session_context}\n\n"
            f"上一轮执行结果：{previous_result}\n\n"
            f"回答要求：{decision.action_detail.get('answer_instruction', '')}"
        )
