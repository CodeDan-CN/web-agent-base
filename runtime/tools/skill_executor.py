from typing import Any

from exception.error_code import BizErrorCode
from runtime.context.assembler import RuntimeContext
from runtime.models import ActionDecision, ActionResult
from runtime.tools.schema_validator import JsonSchemaValidator
from runtime.tools.skill_adapters import build_skill_adapters
from runtime.tools.skill_definition import SkillDefinition


class SkillExecutor:
    """
    Skill 统一执行入口。

    Attributes:
        validator (JsonSchemaValidator): JSON Schema 校验器。
        max_chain_depth (int): 链路 Skill 最大递归深度。
    """

    legacy_skill_names = {
        "content_extract_skill": "content_extract",
    }

    def __init__(self) -> None:
        """
        初始化 SkillExecutor。
        """
        self.validator = JsonSchemaValidator()
        self.max_chain_depth = 8

    async def execute(
        self,
        context: RuntimeContext,
        decision: ActionDecision,
    ) -> ActionResult:
        """
        执行 Loop 决策中的 Skill。

        Args:
            context (RuntimeContext): Runtime 上下文。
            decision (ActionDecision): Action 决策。

        Returns:
            ActionResult: Skill 执行结果。
        """
        skill_id = self.resolve_skill_id(decision.action_detail)
        payload = self._action_input(decision.action_detail)
        return await self.execute_by_skill_id(skill_id, payload, context, depth=0)

    async def execute_by_skill_id(
        self,
        skill_id: str,
        payload: dict[str, Any],
        context: RuntimeContext,
        depth: int,
    ) -> ActionResult:
        """
        根据 Skill ID 执行 Skill。

        Args:
            skill_id (str): Skill ID。
            payload (dict[str, Any]): Skill 输入。
            context (RuntimeContext): Runtime 上下文。
            depth (int): 当前链路深度。

        Returns:
            ActionResult: Skill 执行结果。
        """
        if depth > self.max_chain_depth:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception("Chain Skill 调用过深")
        skill = context.agent_definition.skill_registry.get(skill_id)
        if not skill:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(f"未知 Skill: {skill_id}")
        validation = self.validator.validate(skill.input_schema, payload)
        if not validation.valid:
            if validation.missing_params:
                return ActionResult(
                    status="missing_params",
                    data={},
                    summary="Skill 输入缺少必要参数",
                    missing_params=validation.missing_params,
                    error=None,
                )
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(
                f"Skill 输入不合法: {validation.error}"
            )
        result_payload = await self._execute_skill(skill, payload, context, depth)
        self._validate_output(skill, result_payload)
        return self._to_action_result(result_payload)

    def resolve_skill_id(self, action_detail: dict[str, Any]) -> str:
        """
        从 Action Detail 解析 Skill ID。

        Args:
            action_detail (dict[str, Any]): Action 详情。

        Returns:
            str: Skill ID。
        """
        raw_name = str(
            action_detail.get("skill_id")
            or action_detail.get("name")
            or ""
        ).strip()
        if not raw_name:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception("call_skill 缺少 skill_id")
        return self.legacy_skill_names.get(raw_name, raw_name)

    async def _execute_skill(
        self,
        skill: SkillDefinition,
        payload: dict[str, Any],
        context: RuntimeContext,
        depth: int,
    ) -> dict[str, Any]:
        """
        分派到对应 Adapter。
        """
        adapter_type = str(skill.executor.get("type") or "")
        adapters = build_skill_adapters(context.agent_definition.skill_registry)
        adapter = adapters.get(adapter_type)
        if not adapter:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(
                f"Skill Adapter 不存在: {adapter_type}"
            )
        return await adapter.execute(skill, payload, context, self, depth)

    def _action_input(self, action_detail: dict[str, Any]) -> dict[str, Any]:
        """
        读取 Action 输入对象。
        """
        payload = action_detail.get("input") or {}
        if not isinstance(payload, dict):
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception("Action input 必须是对象")
        return payload

    def _validate_output(self, skill: SkillDefinition, payload: dict[str, Any]) -> None:
        """
        校验 Skill 输出结构。
        """
        validation = self.validator.validate(skill.output_schema, payload)
        if not validation.valid:
            error = validation.error or f"缺少字段: {', '.join(validation.missing_params)}"
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(
                f"Skill 输出不合法: {error}"
            )

    def _to_action_result(self, payload: dict[str, Any]) -> ActionResult:
        """
        转换为 ActionResult。
        """
        missing_params = payload.get("missing_params") or []
        return ActionResult(
            status=str(payload.get("status") or ""),
            data=payload.get("data") or {},
            summary=str(payload.get("summary") or ""),
            missing_params=[str(item) for item in missing_params],
            error=payload.get("error"),
        )
