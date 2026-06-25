import json
from pathlib import Path
from typing import Any

from exception.error_code import BizErrorCode
from runtime.tools.skill_definition import SkillDefinition


class SkillLoader:
    """
    Skill 资产加载器。
    """

    def load_from_agent_dir(self, agent_dir: Path) -> dict[str, SkillDefinition]:
        """
        加载 Agent 目录下的 Skill。

        Args:
            agent_dir (Path): Agent 目录。

        Returns:
            dict[str, SkillDefinition]: Skill ID 到 SkillDefinition 的映射。
        """
        skills_dir = agent_dir / "skills"
        if not skills_dir.exists():
            return {}
        skills: dict[str, SkillDefinition] = {}
        for skill_dir in sorted(item for item in skills_dir.iterdir() if item.is_dir()):
            if skill_dir.name.startswith("."):
                continue
            skill = self._load_skill(skill_dir)
            if skill.skill_id in skills:
                raise BizErrorCode.AGENT_LOAD_ERROR.exception(
                    f"Skill 重复: {skill.skill_id}"
                )
            skills[skill.skill_id] = skill
        return skills

    def _load_skill(self, skill_dir: Path) -> SkillDefinition:
        """
        加载单个 Skill。

        Args:
            skill_dir (Path): Skill 目录。

        Returns:
            SkillDefinition: Skill 定义。
        """
        skill_md = skill_dir / "SKILL.md"
        schema_json = skill_dir / "schema.json"
        if not skill_md.exists():
            raise BizErrorCode.AGENT_LOAD_ERROR.exception(
                f"{skill_dir.name} 缺少 SKILL.md"
            )
        if not schema_json.exists():
            raise BizErrorCode.AGENT_LOAD_ERROR.exception(
                f"{skill_dir.name} 缺少 schema.json"
            )
        instruction = skill_md.read_text(encoding="utf-8").strip()
        if not instruction:
            raise BizErrorCode.AGENT_LOAD_ERROR.exception(
                f"{skill_dir.name} SKILL.md 为空"
            )
        schema = self._read_schema(schema_json)
        skill_id = str(schema.get("skill_id") or "")
        if skill_id != skill_dir.name:
            raise BizErrorCode.AGENT_LOAD_ERROR.exception(
                f"Skill ID 与目录名不一致: {skill_dir.name}"
            )
        executor = self._require_object(schema, "executor", skill_id)
        input_schema = self._require_object(schema, "input_schema", skill_id)
        output_schema = self._require_object(schema, "output_schema", skill_id)
        executor_type = executor.get("type")
        if executor_type not in {"api", "chain", "code"}:
            raise BizErrorCode.AGENT_LOAD_ERROR.exception(
                f"{skill_id} executor.type 非法"
            )
        return SkillDefinition(
            skill_id=skill_id,
            name=str(schema.get("name") or skill_id),
            description=str(schema.get("description") or ""),
            skill_dir=skill_dir,
            instruction=instruction,
            executor=executor,
            input_schema=input_schema,
            output_schema=output_schema,
            references_dir=self._optional_dir(skill_dir / "references"),
            assets_dir=self._optional_dir(skill_dir / "assets"),
        )

    def _read_schema(self, schema_path: Path) -> dict[str, Any]:
        """
        读取 schema.json。

        Args:
            schema_path (Path): schema.json 路径。

        Returns:
            dict[str, Any]: schema 对象。
        """
        try:
            payload = json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BizErrorCode.AGENT_LOAD_ERROR.exception(
                f"{schema_path.parent.name} schema.json 非法"
            ) from exc
        if not isinstance(payload, dict):
            raise BizErrorCode.AGENT_LOAD_ERROR.exception("schema.json 必须是对象")
        return payload

    def _require_object(
        self,
        payload: dict[str, Any],
        key: str,
        skill_id: str,
    ) -> dict[str, Any]:
        """
        读取必填对象字段。

        Args:
            payload (dict[str, Any]): schema。
            key (str): 字段名。
            skill_id (str): Skill ID。

        Returns:
            dict[str, Any]: 对象字段。
        """
        value = payload.get(key)
        if not isinstance(value, dict):
            raise BizErrorCode.AGENT_LOAD_ERROR.exception(f"{skill_id} 缺少 {key}")
        return value

    def _optional_dir(self, path: Path) -> Path | None:
        """
        返回可选目录。

        Args:
            path (Path): 目录路径。

        Returns:
            Path | None: 存在时返回目录，否则返回 None。
        """
        return path if path.exists() and path.is_dir() else None
