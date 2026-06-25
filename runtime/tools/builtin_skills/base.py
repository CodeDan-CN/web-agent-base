from typing import Any


class BaseCodeSkill:
    """
    本地代码 Skill 基类。

    Attributes:
        name (str): executor 名称。
    """

    name: str

    async def run(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        """
        执行代码 Skill。

        Args:
            payload (dict[str, Any]): 输入参数。
            context (Any): Runtime 上下文。

        Returns:
            dict[str, Any]: 标准 SkillResult。
        """
        raise NotImplementedError
