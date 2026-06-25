from runtime.tools.skill_definition import SkillDefinition


class SkillRegistry:
    """
    Skill 注册表。

    Attributes:
        skills (dict[str, SkillDefinition]): Skill 映射。
    """

    def __init__(self, skills: dict[str, SkillDefinition]) -> None:
        """
        初始化注册表。

        Args:
            skills (dict[str, SkillDefinition]): Skill 映射。
        """
        self.skills = skills

    def get(self, skill_id: str) -> SkillDefinition | None:
        """
        获取 Skill。

        Args:
            skill_id (str): Skill ID。

        Returns:
            SkillDefinition | None: Skill 定义。
        """
        return self.skills.get(skill_id)

    def list_for_prompt(self) -> list[dict]:
        """
        构建 Prompt 可用 Skill 目录。

        Returns:
            list[dict]: Skill 目录。
        """
        return [skill.to_catalog_item() for skill in self.skills.values()]
