from dataclasses import dataclass
from typing import Any

from runtime.agents.loader import AgentDefinition, AgentLoader


@dataclass(frozen=True)
class WorkerCatalogItem:
    """
    Worker 目录项。

    Attributes:
        worker_id (str): Worker ID。
        description (str): Worker 简介。
        skill_ids (list[str]): Worker 拥有的 Skill ID 列表。
    """

    worker_id: str
    description: str
    skill_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        """
        转换为可注入 Prompt 的字典。

        Returns:
            dict[str, Any]: Worker 目录项。
        """
        return {
            "worker_id": self.worker_id,
            "description": self.description,
            "skill_ids": self.skill_ids,
        }


class WorkerRegistry:
    """
    Worker Agent 注册表。

    Attributes:
        agent_loader (AgentLoader): Agent 加载器。
    """

    def __init__(self, agent_loader: AgentLoader | None = None) -> None:
        """
        初始化 WorkerRegistry。

        Args:
            agent_loader (AgentLoader | None): Agent 加载器。
        """
        self.agent_loader = agent_loader or AgentLoader()

    def load_workers(self) -> dict[str, AgentDefinition]:
        """
        加载所有 Worker Agent。

        Returns:
            dict[str, AgentDefinition]: Worker 定义。
        """
        return self.agent_loader.load_workers()

    def list_for_prompt(self) -> list[dict[str, Any]]:
        """
        获取可注入 LoopDecider 的 Worker 目录。

        Returns:
            list[dict[str, Any]]: Worker 目录。
        """
        return [
            WorkerCatalogItem(
                worker_id=worker.agent_id,
                description=self._description(worker),
                skill_ids=sorted(worker.skills.keys()),
            ).to_dict()
            for worker in self.load_workers().values()
        ]

    def _description(self, worker: AgentDefinition) -> str:
        """
        从 Agent 资产中提取 Worker 简介。

        Args:
            worker (AgentDefinition): Worker 定义。

        Returns:
            str: Worker 简介。
        """
        agent_md = worker.files.get("Agent.md", "").strip()
        lines = [
            line.strip()
            for line in agent_md.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        return "\n".join(lines[:6])[:600]
