from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillDefinition:
    """
    Skill 定义。

    Attributes:
        skill_id (str): Skill ID。
        name (str): Skill 名称。
        description (str): Skill 描述。
        skill_dir (Path): Skill 资产目录。
        instruction (str): SKILL.md 内容。
        executor (dict[str, Any]): 执行器配置。
        input_schema (dict[str, Any]): 输入 JSON Schema。
        output_schema (dict[str, Any]): 输出 JSON Schema。
        references_dir (Path | None): 参考资料目录。
        assets_dir (Path | None): 静态资源目录。
    """

    skill_id: str
    name: str
    description: str
    skill_dir: Path
    instruction: str
    executor: dict[str, Any]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    references_dir: Path | None
    assets_dir: Path | None

    def to_catalog_item(self) -> dict[str, Any]:
        """
        转换为可注入 Prompt 的 Skill 摘要。

        Returns:
            dict[str, Any]: Skill 摘要。
        """
        properties = self.input_schema.get("properties") or {}
        required = self.input_schema.get("required") or []
        optional = [name for name in properties if name not in required]
        input_fields = [
            {
                "name": name,
                "required": name in required,
                "description": field.get("description", ""),
                "enum": field.get("enum", []),
            }
            for name, field in properties.items()
            if isinstance(field, dict)
        ]
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "executor_type": self.executor.get("type"),
            "required_input": required,
            "optional_input": optional,
            "input_fields": input_fields,
        }
