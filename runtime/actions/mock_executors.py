from typing import Any

from runtime.models import ActionResult


class ContentExtractMockExecutor:
    """
    文本提取 mock executor。
    """

    name = "content_extract_skill"

    async def execute(self, payload: dict[str, Any]) -> ActionResult:
        """
        执行文本提取 mock。

        Args:
            payload (dict[str, Any]): 输入参数。

        Returns:
            ActionResult: 执行结果。
        """
        user_message = str(payload.get("user_message", ""))
        content = str(payload.get("content") or "").strip()
        content = content or self._extract_content_from_message(user_message)
        if "损坏" in user_message or "无法读取" in user_message:
            return ActionResult(
                status="failed",
                summary="content_extract_skill 无法读取不可用内容",
                error="unreadable_content",
            )
        if not content:
            return ActionResult(
                status="missing_params",
                summary="缺少需要提取的原始文本",
                missing_params=["content"],
            )
        points = self._build_points(content)
        return ActionResult(
            status="success",
            summary="content_extract_skill 提取完成",
            data={"key_points": points, "content": content},
        )

    def _extract_content_from_message(self, message: str) -> str:
        """
        从自然语言消息中提取文本内容。

        Args:
            message (str): 用户消息。

        Returns:
            str: 提取出的文本内容。
        """
        markers = ["原文是：", "原文是:", "内容：", "内容:", "：", ":"]
        for marker in markers:
            if marker in message:
                return message.split(marker, 1)[1].strip()
        return ""

    def _build_points(self, content: str) -> list[str]:
        """
        构建 mock 要点。

        Args:
            content (str): 原始文本。

        Returns:
            list[str]: 要点列表。
        """
        fragments = [
            item.strip(" ，。；;\n")
            for item in content.replace("、", "，").replace("，", "\n").split("\n")
        ]
        points = [item for item in fragments if item]
        return points[:6] or [content[:120]]


class PlanningMockExecutor:
    """
    规划分析 mock executor。
    """

    name = "planning_worker"

    async def execute(self, payload: dict[str, Any]) -> ActionResult:
        """
        执行规划分析 mock。

        Args:
            payload (dict[str, Any]): 输入参数。

        Returns:
            ActionResult: 执行结果。
        """
        user_message = str(payload.get("user_message", ""))
        if "无法访问" in user_message or "外部私有系统实时数据" in user_message:
            return ActionResult(
                status="failed",
                summary="planning_worker 无法访问外部私有系统实时数据",
                error="external_dependency_unavailable",
            )
        goal = str(payload.get("goal") or "").strip()
        background = str(payload.get("background") or "").strip()
        constraints = payload.get("constraints") or {}
        goal = goal or self._infer_goal(user_message)
        background = background or self._infer_background(user_message, constraints)
        missing_params = self._missing_params(goal, background, user_message)
        if missing_params:
            return ActionResult(
                status="missing_params",
                summary="缺少方案目标、约束或背景信息",
                missing_params=missing_params,
            )
        plan = self._build_plan(goal, background)
        return ActionResult(
            status="success",
            summary="planning_worker 规划完成",
            data={"goal": goal, "background": background, "plan": plan},
        )

    def _infer_goal(self, message: str) -> str:
        """
        从消息中推断目标。

        Args:
            message (str): 用户消息。

        Returns:
            str: 目标。
        """
        if any(keyword in message for keyword in ["想学", "目标是", "完成", "落地"]):
            return message
        return ""

    def _infer_background(self, message: str, constraints: dict[str, Any]) -> str:
        """
        从消息中推断背景。

        Args:
            message (str): 用户消息。
            constraints (dict[str, Any]): 约束。

        Returns:
            str: 背景。
        """
        if constraints:
            return str(constraints)
        if any(keyword in message for keyword in ["三个月", "每周", "两周", "团队", "目前"]):
            return message
        return ""

    def _missing_params(self, goal: str, background: str, message: str) -> list[str]:
        """
        判断缺失参数。

        Args:
            goal (str): 目标。
            background (str): 背景。
            message (str): 用户消息。

        Returns:
            list[str]: 缺失参数。
        """
        missing: list[str] = []
        if not goal:
            missing.append("goal")
        if not background:
            missing.append("background")
        if message.strip() in {"帮我做一个实施方案", "帮我规划一下学习路线", "我想学 Python"}:
            if "constraints" not in missing:
                missing.append("constraints")
        return missing

    def _build_plan(self, goal: str, background: str) -> list[dict[str, str]]:
        """
        构建 mock 计划。

        Args:
            goal (str): 目标。
            background (str): 背景。

        Returns:
            list[dict[str, str]]: 计划步骤。
        """
        return [
            {"step": "1", "title": "明确目标和边界", "detail": goal[:160]},
            {"step": "2", "title": "拆分关键任务", "detail": background[:160]},
            {"step": "3", "title": "按时间推进", "detail": "按优先级执行并定期复盘。"},
        ]
